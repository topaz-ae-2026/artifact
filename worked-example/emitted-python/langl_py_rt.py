from __future__ import annotations

from dataclasses import dataclass, make_dataclass
import inspect
import json
import math
import struct
import types


INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1
I128_MIN = -(1 << 127)
I128_MAX = (1 << 127) - 1
U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1
_NO_TRACE_VALUE = object()
STRUCT_FUEL = 100_000
STRUCT_DEPTH = 128


class _StructBudget:
    __slots__ = ("fuel",)

    def __init__(self, fuel: int = STRUCT_FUEL) -> None:
        self.fuel = fuel

    def consume(self, depth: int, span: tuple[int, int, int]) -> None:
        if self.fuel <= 0 or depth > STRUCT_DEPTH:
            L_fault("L5007", "comparison exceeded the structural budget (cyclic value?)", span)
        self.fuel -= 1


class _LUnit:
    __slots__ = ()

    def __repr__(self) -> str:
        return "()"


class _LNull:
    __slots__ = ()

    def __repr__(self) -> str:
        return "null"


L_UNIT = _LUnit()
L_NULL = _LNull()
L_ANONYMOUS_VARIADIC_TAIL_KW = "__L_variadic_tail__"


@dataclass(frozen=True, slots=True)
class LFault(Exception):
    code: str
    message: str
    span: tuple[int, int, int]

    def to_json(self) -> dict[str, object]:
        file, lo, hi = self.span
        return {
            "code": self.code,
            "message": self.message,
            "span": {"file": file, "lo": lo, "hi": hi},
        }


@dataclass(frozen=True, slots=True)
class Some:
    value: object


@dataclass(frozen=True, slots=True)
class Ok:
    value: object


@dataclass(frozen=True, slots=True)
class Err:
    value: object


@dataclass(frozen=True, slots=True)
class LNewtype:
    newtype_id: str
    value: object


@dataclass(frozen=True, slots=True)
class LEnum:
    enum_id: str
    variant: str
    variant_index: int
    payloads: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class LReturn(Exception):
    value: object


@dataclass(frozen=True, slots=True)
class LLoopBreak(Exception):
    label: str | None
    value: object


@dataclass(frozen=True, slots=True)
class LLoopContinue(Exception):
    label: str | None


@dataclass(frozen=True, slots=True)
class LFile:
    host: object
    handle: int


@dataclass(frozen=True, slots=True)
class LBytes:
    data: bytes


@dataclass(frozen=True, slots=True)
class LFloatKey:
    bits: int
    value: float

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LFloatKey):
            return False
        if math.isnan(self.value) or math.isnan(other.value):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        if math.isnan(self.value):
            return hash(("f64", self.bits))
        return hash(("f64", self.value))


@dataclass(slots=True)
class LMap:
    entries: list[tuple[object, object]]


@dataclass(slots=True)
class LSet:
    items: list[object]

    def __iter__(self):
        return (_key_to_value(item) for item in self.items)


@dataclass(frozen=True, slots=True)
class LRange:
    lo: int
    hi: int
    inclusive: bool
    step: int

    def __iter__(self):
        if self.step == 0:
            L_fault("L4003", "range step must not be zero (§10)", (0, 0, 0))
        value = self.lo
        while True:
            if self.step > 0:
                within = value <= self.hi if self.inclusive else value < self.hi
            else:
                within = value >= self.hi if self.inclusive else value > self.hi
            if not within:
                return
            yield value
            next_value = value + self.step
            if next_value < INT_MIN or next_value > INT_MAX:
                return
            value = next_value


@dataclass(frozen=True, slots=True)
class LComposed:
    first: object
    second: object
    span: tuple[int, int, int]

    def __call__(self, *args, **kwargs):
        return self.call_with_span(args, kwargs, self.span)

    def call_with_span(self, args: tuple[object, ...], kwargs: dict[str, object], span: tuple[int, int, int]) -> object:
        mid = L_call(self.first, args, kwargs, span)
        return L_call(self.second, (mid,), {}, span)

    def __call_cooperative__(self, *args, **kwargs):
        mid = yield from L_call_cooperative(self.first, args, kwargs, self.span)
        return (yield from L_call_cooperative(self.second, (mid,), {}, self.span))


@dataclass(frozen=True, slots=True)
class LHostCallable:
    fn: object
    host: object
    cooperative_fn: object | None = None
    variadic_py_name: str | None = None

    def _rewrite_anonymous_variadic_tail(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> tuple[tuple[object, ...], dict[str, object]]:
        if L_ANONYMOUS_VARIADIC_TAIL_KW not in kwargs:
            return args, kwargs
        tail = kwargs.pop(L_ANONYMOUS_VARIADIC_TAIL_KW)
        if self.variadic_py_name is not None:
            kwargs[self.variadic_py_name] = tail
            return args, kwargs
        # Fallback for non-langl Python callables that satisfy a variadic function type.
        return args + tuple(tail), kwargs

    def __call__(self, *args, **kwargs):
        args, kwargs = self._rewrite_anonymous_variadic_tail(args, kwargs)
        return self.fn(self.host, *args, **kwargs)

    def __call_cooperative__(self, *args, **kwargs):
        args, kwargs = self._rewrite_anonymous_variadic_tail(args, kwargs)
        if self.cooperative_fn is not None:
            return (yield from self.cooperative_fn(self.host, *args, **kwargs))
        return self.fn(self.host, *args, **kwargs)


@dataclass(frozen=True, slots=True)
class LCooperativeCallable:
    fn: object
    cooperative_fn: object

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __call_cooperative__(self, *args, **kwargs):
        result = self.cooperative_fn(*args, **kwargs)
        if isinstance(result, types.GeneratorType):
            return (yield from result)
        return result


@dataclass(frozen=True, slots=True)
class LExternFunction:
    module: str
    function: str
    span: tuple[int, int, int]

    def __call__(self, host: object, *args):
        try:
            return host.extern_call(self.module, self.function, args)
        except ValueError as error:
            L_fault("L5032", str(error), self.span)


def L_concurrent_join(arms: list[tuple[str, object]]) -> list[object]:
    pending: list[tuple[int, str, object]] = []
    results: list[object] = [L_UNIT for _ in arms]
    for index, (name, thunk) in enumerate(arms):
        pending.append((index, name, thunk()))
    while pending:
        cursor = 0
        while cursor < len(pending):
            index, _name, gen = pending[cursor]
            try:
                next(gen)
                cursor += 1
            except StopIteration as done:
                results[index] = done.value
                pending.pop(cursor)
    return results


@dataclass(frozen=True, slots=True)
class ExternSandboxPolicy:
    module: str
    kind: str
    artifact_path: str | None
    fuel: int | None
    memory_bytes: int | None


@dataclass(frozen=True, slots=True)
class LJsonNumber:
    lexeme: str
    int_value: int | None


@dataclass(frozen=True, slots=True)
class LJson:
    kind: str
    value: object = None


@dataclass(frozen=True, slots=True)
class LJsonParseErrorRecord:
    _t_636f6c756d6e: int
    _t_6c696e65: int
    _t_6d657373616765: str


_RECORD_CLASS_CACHE: dict[tuple[str | None, tuple[tuple[str, str], ...]], type] = {}


class ExternReplayStore:
    def __init__(
        self,
        entries: dict[tuple[str, str, str], object] | None = None,
        policies: dict[str, ExternSandboxPolicy] | None = None,
    ) -> None:
        self._entries: dict[tuple[str, str, str], object] = dict(entries or {})
        self._policies = policies

    @classmethod
    def parse_jsonl(
        cls,
        text: str,
        policies_json: str | None = None,
    ) -> ExternReplayStore:
        entries: dict[tuple[str, str, str], object] = {}
        for index, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                node = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "extern replay line "
                    + str(index)
                    + ": invalid JSON at line "
                    + str(error.lineno)
                    + ", column "
                    + str(error.colno)
                    + ": "
                    + error.msg
                ) from None
            if not isinstance(node, dict):
                raise ValueError("extern replay line " + str(index) + ": row must be an object")
            if set(node.keys()) != {"module", "function", "args", "result"}:
                raise ValueError(
                    "extern replay line "
                    + str(index)
                    + ": expected fields args, function, module, result"
                )
            module = node["module"]
            function = node["function"]
            args_node = node["args"]
            if not isinstance(module, str):
                raise ValueError("extern replay line " + str(index) + ": `module` must be a string")
            if not isinstance(function, str):
                raise ValueError("extern replay line " + str(index) + ": `function` must be a string")
            if not isinstance(args_node, list):
                raise ValueError("extern replay line " + str(index) + ": `args` must be an array")
            args = tuple(_abi_decode_value(arg, "line " + str(index) + ".args[" + str(i) + "]", 0) for i, arg in enumerate(args_node))
            result = _abi_decode_value(node["result"], "line " + str(index) + ".result", 0)
            key = (module, function, _abi_args_encode(args))
            if key in entries:
                raise ValueError(
                    "extern replay line "
                    + str(index)
                    + ": duplicate row for `"
                    + module
                    + "."
                    + function
                    + "` with canonical ABI args `"
                    + key[2]
                    + "`"
                )
            entries[key] = result
        return cls(entries, _parse_extern_sandbox_policies(policies_json))

    def call(self, module: str, function: str, args: tuple[object, ...]) -> object:
        args_json = _abi_args_encode(args)
        key = (module, function, args_json)
        policy = None
        if self._policies is not None:
            policy = self._policies.get(module)
            if policy is None:
                raise ValueError("extern sandbox policy for `" + module + "` is not available")
            _validate_extern_sandbox_policy(policy)
        if key not in self._entries:
            raise ValueError(
                "extern replay has no row for `"
                + module
                + "."
                + function
                + "` with canonical ABI args `"
                + args_json
                + "`"
            )
        result = self._entries[key]
        if policy is not None:
            _enforce_extern_replay_budget(policy, module, function, args, args_json, result)
        return result


class Host:
    def __init__(
        self,
        stdin_text: str,
        files: dict[str, str] | None = None,
        extern_replay_jsonl: str | None = None,
        extern_sandbox_policies_json: str | None = None,
    ) -> None:
        self._stdin_text = stdin_text
        self.stdout: list[str] = []
        self.defer_errors: list[dict[str, object]] = []
        self._files: dict[str, str] = dict(files or {})
        self._open: dict[int, tuple[str, bool]] = {}
        self._next_handle = 0
        self._extern_replay = ExternReplayStore.parse_jsonl(
            extern_replay_jsonl or "",
            extern_sandbox_policies_json,
        )

    def input(self) -> str:
        return self._stdin_text

    def trace_files(self) -> list[dict[str, object]]:
        return [
            {"path": path, "content": L_trace_value(content)}
            for path, content in sorted(self._files.items())
        ]

    def print(self, value: object, span: tuple[int, int, int]) -> object:
        if not isinstance(value, str):
            L_fault("L5001", "`print` is string-only; interpolate instead (§22.2)", span)
        self.stdout.append(value)
        return L_UNIT

    def open_file(self, path: object, span: tuple[int, int, int]) -> Ok | Err:
        if not isinstance(path, str):
            L_fault("L5001", "`open` takes a `string`, found `" + L_kind(path) + "`", span)
        if path not in self._files:
            return Err("cannot open `" + path + "`: not found")
        self._next_handle += 1
        self._open[self._next_handle] = (path, False)
        return Ok(LFile(self, self._next_handle))

    def read_file(self, handle: int) -> Ok | Err:
        entry = self._open.get(handle)
        if entry is None:
            return Err("file is not open")
        path, closed = entry
        if closed:
            return Err("file is closed")
        if path not in self._files:
            return Err("cannot read `" + path + "`")
        return Ok(self._files[path])

    def write_file(self, handle: int, value: object, span: tuple[int, int, int]) -> Ok | Err:
        if not isinstance(value, str):
            L_fault(
                "L5001",
                "`file.write` takes a `string`, found `" + L_kind(value) + "`",
                span,
            )
        entry = self._open.get(handle)
        if entry is None:
            return Err("file is not open")
        path, closed = entry
        if closed:
            return Err("file is closed")
        self._files[path] = value
        return Ok(L_UNIT)

    def close_file(self, handle: int) -> None:
        entry = self._open.get(handle)
        if entry is not None:
            path, _closed = entry
            self._open[handle] = (path, True)

    def fs_read_text(self, path: str) -> Ok | Err:
        opened = self.open_file(path, (0, 0, 0))
        if isinstance(opened, Err):
            return opened
        read = self.read_file(opened.value.handle)
        self.close_file(opened.value.handle)
        return read

    def fs_write_text(self, path: str, text: str) -> Ok | Err:
        opened = self.open_file(path, (0, 0, 0))
        if isinstance(opened, Err):
            return opened
        written = self.write_file(opened.value.handle, text, (0, 0, 0))
        self.close_file(opened.value.handle)
        return written

    def fs_read_bytes(self, path: str) -> Ok | Err:
        if path not in self._files:
            return Err("cannot read `" + path + "`")
        return Ok(LBytes(self._files[path].encode("utf-8")))

    def fs_write_bytes(self, path: str, value: LBytes) -> Ok | Err:
        self._files[path] = value.data.decode("utf-8", "replace")
        return Ok(L_UNIT)

    def fs_list(self, path: str) -> Ok | Err:
        if path == "" or path == ".":
            prefix = ""
        elif path.endswith("/"):
            prefix = path
        else:
            prefix = path + "/"
        entries: dict[str, object] = {}
        for file_path, contents in self._files.items():
            if not file_path.startswith(prefix):
                continue
            rest = file_path[len(prefix) :]
            if rest == "":
                continue
            if "/" in rest:
                dirname = rest.split("/", 1)[0]
                entries[dirname] = _fs_dir_entry(dirname, "directory", None)
            else:
                entries[rest] = _fs_dir_entry(rest, "file", len(contents.encode("utf-8")))
        if not entries and path not in self._files:
            return Err("cannot list `" + path + "`")
        return Ok([entries[name] for name in sorted(entries)])

    def extern_call(self, module: str, function: str, args: tuple[object, ...]) -> object:
        return self._extern_replay.call(module, function, args)

    def trace_ok(self, value: object = _NO_TRACE_VALUE) -> str:
        return L_trace_line("ok", self.stdout, self.trace_files(), self.defer_errors, None, value)

    def trace_fault(self, fault: LFault) -> str:
        return L_trace_line(
            "fault",
            self.stdout,
            self.trace_files(),
            self.defer_errors,
            fault.to_json(),
        )

    def defer_error(self, rendered: str, fault: LFault | None = None) -> None:
        entry: dict[str, object] = {"rendered": rendered}
        if fault is not None:
            entry["fault"] = fault.to_json()
        self.defer_errors.append(entry)


def L_trace_line(
    status: str,
    stdout: list[str],
    files: list[dict[str, object]],
    defer_errors: list[dict[str, object]],
    fault: dict[str, object] | None,
    value: object = _NO_TRACE_VALUE,
) -> str:
    # Trace v1 key order is stable for readable diffs. Consumers parse structurally.
    trace: dict[str, object] = {
        "v": 1,
        "status": status,
        "stdout": stdout,
        "files": files,
        "defer_errors": defer_errors,
        "fault": fault,
    }
    if value is not _NO_TRACE_VALUE:
        trace["value"] = L_trace_value(value)
    return json.dumps(
        trace,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def L_f64_from_bits(bits: int) -> float:
    if type(bits) is not int or bits < 0 or bits > U64_MAX:
        raise ValueError("f64 bits must be a u64")
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def L_f64_bits(value: object) -> int:
    if type(value) is not float:
        raise TypeError("expected float")
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def L_trace_value(value: object) -> dict[str, object]:
    if type(value) is float:
        return {"f64": f"{L_f64_bits(value):016x}"}
    if type(value) is bool:
        return {"bool": value}
    if type(value) is int:
        return {"int": value}
    if isinstance(value, str):
        return {"str": value}
    if value is L_UNIT or value is L_NULL or value is None:
        return {"null": None}
    if isinstance(value, Some):
        return {"some": L_trace_value(value.value)}
    if isinstance(value, Ok):
        return {"result": {"ok": L_trace_value(value.value)}}
    if isinstance(value, Err):
        return {"result": {"err": L_trace_value(value.value)}}
    if isinstance(value, LBytes):
        return {"bytes": L_bytes_to_hex(value)}
    if _is_langl_enum(value):
        return {
            "enum": {
                "id": value.enum_id,
                "variant": value.variant,
                "index": value.variant_index,
                "payloads": [L_trace_value(item) for item in value.payloads],
            }
        }
    if isinstance(value, LMap):
        return {
            "map": [
                {"key": L_trace_value(_key_to_value(key)), "value": L_trace_value(item)}
                for key, item in value.entries
            ]
        }
    if isinstance(value, LSet):
        return {"set": [L_trace_value(_key_to_value(key)) for key in value.items]}
    if isinstance(value, LRange):
        return {
            "range": {
                "lo": value.lo,
                "hi": value.hi,
                "inclusive": value.inclusive,
                "step": value.step,
            }
        }
    if isinstance(value, list):
        return {"list": [L_trace_value(item) for item in value]}
    if _is_langl_record(value):
        return {
            "record": {
                source_field: L_trace_value(getattr(value, py_field))
                for py_field, source_field in sorted(
                    value.__langl_record_fields__, key=lambda item: item[1]
                )
            }
        }
    raise TypeError("unsupported trace value")


def L_format_f64(value: object) -> str:
    if type(value) is not float:
        raise TypeError("expected float")
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if value.is_integer() and abs(value) < 1e15:
        return f"{value:.1f}"
    return _L_expand_shortest_float_repr(repr(value))


def _L_expand_shortest_float_repr(text: str) -> str:
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    lower = text.lower()
    if "e" not in lower:
        if text.endswith(".0"):
            text = text[:-2]
        return sign + text
    mantissa, exponent_text = lower.split("e", 1)
    exponent = int(exponent_text)
    if "." in mantissa:
        whole, frac = mantissa.split(".", 1)
    else:
        whole, frac = mantissa, ""
    digits = whole + frac
    decimal_pos = len(whole) + exponent
    if decimal_pos <= 0:
        body = "0." + ("0" * (-decimal_pos)) + digits
    elif decimal_pos >= len(digits):
        body = digits + ("0" * (decimal_pos - len(digits)))
    else:
        body = digits[:decimal_pos] + "." + digits[decimal_pos:]
    return sign + body


def L_fault(code: str, message: str, span: tuple[int, int, int]) -> None:
    raise LFault(code, message, span)


def L_try(value: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Ok):
        return value.value
    if isinstance(value, Err):
        raise LReturn(value)
    L_fault("L5001", "`?` requires a `Result`, found `" + L_kind(value) + "` (§13)", span)


def L_spread_values(value: object, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "a spread argument must be an Array (§5)", span)
    return list(value)


def L_call_order_fault(
    _evaluated: list[object],
    message: str,
    span: tuple[int, int, int],
) -> object:
    L_fault("L5004", message, span)


def L_nonvariadic_spread_call(
    positional: list[object],
    _spread_tail: list[object],
    _named_values: list[tuple[str, object]],
    arity: int,
    span: tuple[int, int, int],
) -> object:
    if len(positional) > arity:
        L_fault("L5004", f"expected {arity} argument(s), found more", span)
    L_fault("L5004", "spread arguments require a variadic parameter (§5)", span)


def L_nonvariadic_static_spread_call(
    _positional: list[object],
    _spread_tail: list[object],
    _named_values: list[tuple[str, object]],
    span: tuple[int, int, int],
) -> object:
    L_fault("L5004", "spread arguments require a variadic parameter (§5)", span)


def L_for_items(value: object, span: tuple[int, int, int]) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, LSet):
        return list(value)
    if isinstance(value, LRange):
        return list(value)
    if isinstance(value, LMap):
        L_fault("L5001", "`for` over `Map` is a static error; iterate `m.keys` (§10)", span)
    if isinstance(value, str):
        L_fault("L5001", "strings are not `for`-iterable; use `s.scalars()` (§10)", span)
    L_fault("L5001", "`" + L_kind(value) + "` is not `for`-iterable (§10)", span)


def L_in(item: object, value: object, span: tuple[int, int, int]) -> bool:
    if isinstance(value, LSet):
        return L_set_contains(value, item, span)
    if isinstance(value, LMap):
        L_fault("L5001", "`x in map` is a static error; use `x in map.keys` (§9)", span)
    for candidate in L_for_items(value, span):
        if L_eq(item, candidate, span):
            return True
    return False


def L_for_pattern(condition: object, span: tuple[int, int, int]) -> bool:
    if condition is True:
        return True
    L_fault("L5001", "`for` pattern did not match an element", span)


def L_let_pattern(condition: object, span: tuple[int, int, int]) -> bool:
    if condition is True:
        return True
    L_fault("L5001", "`let` pattern did not match the value (§4)", span)


def L_call(value: object, args: tuple[object, ...], kwargs: dict[str, object], span: tuple[int, int, int]) -> object:
    if isinstance(value, LComposed):
        return value.call_with_span(args, kwargs, span)
    if not callable(value):
        L_fault("L5005", "`" + L_kind(value) + "` is not callable", span)
    return value(*args, **kwargs)


def L_call_cooperative(value: object, args: tuple[object, ...], kwargs: dict[str, object], span: tuple[int, int, int]):
    cooperative_call = getattr(value, "__call_cooperative__", None)
    if cooperative_call is not None:
        return (yield from cooperative_call(*args, **kwargs))
    if not callable(value):
        L_fault("L5005", "`" + L_kind(value) + "` is not callable", span)
    result = value(*args, **kwargs)
    if isinstance(result, types.GeneratorType):
        return (yield from result)
    return result


def _L_call_callback_co(callback: object, args: tuple[object, ...], span: tuple[int, int, int]):
    return (yield from L_call_cooperative(callback, args, {}, span))


def L_compose(first: object, second: object, span: tuple[int, int, int]) -> LComposed:
    return LComposed(first, second, span)


def L_host_callable(
    fn: object,
    host: object,
    cooperative_fn: object | None = None,
    variadic_py_name: str | None = None,
) -> LHostCallable:
    return LHostCallable(fn, host, cooperative_fn, variadic_py_name)


def L_cooperative_callable(fn: object, cooperative_fn: object) -> LCooperativeCallable:
    return LCooperativeCallable(fn, cooperative_fn)


def L_extern_function(module: str, function: str, span: tuple[int, int, int]) -> LExternFunction:
    return LExternFunction(module, function, span)


def L_run_defer(host: Host, thunk) -> None:
    try:
        value = thunk()
    except LFault as fault:
        host.defer_error(fault.code + ": " + fault.message, fault)
        return
    except LReturn as returned:
        host.defer_error(L_render(returned.value))
        return
    if isinstance(value, Err):
        host.defer_error(L_render(value.value))


def L_file_read(value: object, member_span: tuple[int, int, int]) -> Ok | Err:
    if not isinstance(value, LFile):
        L_no_member(value, "read", member_span)
    return value.host.read_file(value.handle)


def L_file_write(
    value: object,
    text: object,
    member_span: tuple[int, int, int],
    call_span: tuple[int, int, int],
) -> Ok | Err:
    if not isinstance(value, LFile):
        L_no_member(value, "write", member_span)
    return value.host.write_file(value.handle, text, call_span)


def L_file_close(value: object, member_span: tuple[int, int, int]) -> object:
    if not isinstance(value, LFile):
        L_no_member(value, "close", member_span)
    value.host.close_file(value.handle)
    return L_UNIT


def _fs_path_arg(value: object, method: str, span: tuple[int, int, int]) -> str:
    if isinstance(value, str):
        return value
    L_fault(
        "L5001",
        "`FS." + method + "` parameter `path` expects string or Path; found `" + L_kind(value) + "`",
        span,
    )


def _fs_bytes_arg(value: object, method: str, span: tuple[int, int, int]) -> LBytes:
    if isinstance(value, LBytes):
        return value
    L_fault(
        "L5001",
        "`FS." + method + "` takes `Bytes`, found `" + L_kind(value) + "`",
        span,
    )


def _fs_dir_entry(name: str, kind: str, size_bytes: int | None) -> object:
    fields = (
        ("_t_6b696e64", "kind"),
        ("_t_6e616d65", "name"),
        ("_t_73697a654279746573", "sizeBytes"),
    )
    cls = _record_class_for_fields(fields)
    return cls(
        _t_6b696e64=kind,
        _t_6e616d65=name,
        _t_73697a654279746573=Some(size_bytes) if size_bytes is not None else None,
    )


def L_fs_read_text(host: Host, path: object, span: tuple[int, int, int]) -> Ok | Err:
    return host.fs_read_text(_fs_path_arg(path, "readText", span))


def L_fs_write_text(
    host: Host,
    path: object,
    text: object,
    span: tuple[int, int, int],
) -> Ok | Err:
    path = _fs_path_arg(path, "writeText", span)
    if not isinstance(text, str):
        L_fault(
            "L5001",
            "`FS.writeText` takes `text: string`, found `" + L_kind(text) + "`",
            span,
        )
    return host.fs_write_text(path, text)


def L_fs_read_bytes(host: Host, path: object, span: tuple[int, int, int]) -> Ok | Err:
    return host.fs_read_bytes(_fs_path_arg(path, "readBytes", span))


def L_fs_write_bytes(
    host: Host,
    path: object,
    bytes_value: object,
    span: tuple[int, int, int],
) -> Ok | Err:
    path = _fs_path_arg(path, "writeBytes", span)
    return host.fs_write_bytes(path, _fs_bytes_arg(bytes_value, "writeBytes", span))


def L_fs_list(host: Host, path: object, span: tuple[int, int, int]) -> Ok | Err:
    return host.fs_list(_fs_path_arg(path, "list", span))


def L_no_member(value: object, member: str, span: tuple[int, int, int]) -> None:
    L_fault(
        "L5006",
        "`" + L_kind(value) + "` has no member `" + member + "` (or it lands in a later slice)",
        span,
    )


_HEX = "0123456789abcdef"
_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _bytes_receiver(value: object, name: str, span: tuple[int, int, int]) -> LBytes:
    if not isinstance(value, LBytes):
        L_fault(
            "L5001",
            "`Bytes." + name + "` takes a `Bytes`, found `" + L_kind(value) + "`",
            span,
        )
    return value


def _bytes_str_arg(value: object, name: str, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault(
            "L5001",
            "`Bytes." + name + "` takes a `string`, found `" + L_kind(value) + "`",
            span,
        )
    return value


def _hex_nibble(ch: str) -> int | None:
    code = ord(ch)
    if 48 <= code <= 57:
        return code - 48
    if 97 <= code <= 102:
        return code - 87
    if 65 <= code <= 70:
        return code - 55
    return None


def L_bytes_to_hex(value: object, span: tuple[int, int, int] | None = None) -> str:
    raw = _bytes_receiver(value, "toHex", span or (0, 0, 0)).data
    out: list[str] = []
    for byte in raw:
        out.append(_HEX[byte >> 4])
        out.append(_HEX[byte & 0x0F])
    return "".join(out)


def _bytes_to_base64(raw: bytes) -> str:
    out: list[str] = []
    for i in range(0, len(raw), 3):
        chunk = raw[i : i + 3]
        b0 = chunk[0]
        b1 = chunk[1] if len(chunk) > 1 else 0
        b2 = chunk[2] if len(chunk) > 2 else 0
        n = (b0 << 16) | (b1 << 8) | b2
        out.append(_BASE64_ALPHABET[(n >> 18) & 0x3F])
        out.append(_BASE64_ALPHABET[(n >> 12) & 0x3F])
        out.append(_BASE64_ALPHABET[(n >> 6) & 0x3F] if len(chunk) > 1 else "=")
        out.append(_BASE64_ALPHABET[n & 0x3F] if len(chunk) > 2 else "=")
    return "".join(out)


def _base64_sextet(ch: str) -> int | None:
    code = ord(ch)
    if 65 <= code <= 90:
        return code - 65
    if 97 <= code <= 122:
        return code - 71
    if 48 <= code <= 57:
        return code + 4
    if ch == "+":
        return 62
    if ch == "/":
        return 63
    return None


def L_bytes_empty() -> LBytes:
    return LBytes(b"")


def L_bytes_encode_utf8(value: object, span: tuple[int, int, int]) -> LBytes:
    return LBytes(_bytes_str_arg(value, "encodeUtf8", span).encode("utf-8"))


def L_bytes_from_array(value: object, span: tuple[int, int, int]) -> Ok | Err:
    if not isinstance(value, list):
        L_fault(
            "L5001",
            "`Bytes.fromArray` takes an `Array<int>`, found `" + L_kind(value) + "`",
            span,
        )
    out = bytearray()
    for idx, item in enumerate(value):
        if type(item) is int and 0 <= item <= 255:
            out.append(item)
        elif type(item) is int:
            return Err("Bytes.fromArray: value at index " + str(idx) + " is outside 0..255")
        else:
            return Err(
                "Bytes.fromArray: value at index "
                + str(idx)
                + " is `"
                + L_kind(item)
                + "`, expected `int`"
            )
    return Ok(LBytes(bytes(out)))


def L_bytes_from_hex(value: object, span: tuple[int, int, int]) -> Ok | Err:
    text = _bytes_str_arg(value, "fromHex", span)
    if len(text) % 2 != 0:
        return Err("Bytes.fromHex: odd-length hex string")
    out = bytearray()
    for i in range(0, len(text), 2):
        hi = _hex_nibble(text[i])
        lo = _hex_nibble(text[i + 1])
        if hi is None or lo is None:
            return Err("Bytes.fromHex: invalid hex digit")
        out.append((hi << 4) | lo)
    return Ok(LBytes(bytes(out)))


def L_bytes_to_base64(value: object, span: tuple[int, int, int]) -> str:
    return _bytes_to_base64(_bytes_receiver(value, "toBase64", span).data)


def L_bytes_from_base64(value: object, span: tuple[int, int, int]) -> Ok | Err:
    text = _bytes_str_arg(value, "fromBase64", span)
    if text == "":
        return Ok(LBytes(b""))
    if len(text) % 4 != 0:
        return Err("Bytes.fromBase64: length is not a multiple of 4")
    pad = text.count("=")
    if pad > 2 or "=" in text[: len(text) - pad]:
        return Err("Bytes.fromBase64: misplaced padding")
    out = bytearray()
    for i in range(0, len(text), 4):
        group = text[i : i + 4]
        pads = group.count("=")
        sextets = [0, 0, 0, 0]
        for j, ch in enumerate(group):
            if ch == "=":
                continue
            value = _base64_sextet(ch)
            if value is None:
                return Err("Bytes.fromBase64: invalid base64 character")
            sextets[j] = value
        n = (sextets[0] << 18) | (sextets[1] << 12) | (sextets[2] << 6) | sextets[3]
        if pads == 0:
            out.append((n >> 16) & 0xFF)
            out.append((n >> 8) & 0xFF)
            out.append(n & 0xFF)
        elif pads == 1:
            if n & 0xFF:
                return Err("Bytes.fromBase64: non-canonical padding bits")
            out.append((n >> 16) & 0xFF)
            out.append((n >> 8) & 0xFF)
        elif pads == 2:
            if n & 0xFFFF:
                return Err("Bytes.fromBase64: non-canonical padding bits")
            out.append((n >> 16) & 0xFF)
        else:
            return Err("Bytes.fromBase64: misplaced padding")
    return Ok(LBytes(bytes(out)))


def L_bytes_decode_utf8(value: object, span: tuple[int, int, int]) -> Ok | Err:
    raw = _bytes_receiver(value, "decodeUtf8", span).data
    try:
        return Ok(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return Err("Bytes.decodeUtf8: invalid UTF-8")


def L_bytes_length(value: object, span: tuple[int, int, int]) -> int:
    return len(_bytes_receiver(value, "length", span).data)


def L_bytes_is_empty(value: object, span: tuple[int, int, int]) -> bool:
    return len(_bytes_receiver(value, "isEmpty", span).data) == 0


def L_bytes_get(value: object, index: object, span: tuple[int, int, int]) -> Some | None:
    raw = _bytes_receiver(value, "get", span).data
    if type(index) is not int:
        L_fault("L5001", "`Bytes.get` takes an `int` index", span)
    if 0 <= index < len(raw):
        return Some(raw[index])
    return None


def L_bytes_slice(value: object, start: object, end: object, span: tuple[int, int, int]) -> LBytes:
    raw = _bytes_receiver(value, "slice", span).data
    if type(start) is not int:
        L_fault(
            "L5001",
            "`Bytes.slice` takes `int` bounds, found `" + L_kind(start) + "`",
            span,
        )
    if type(end) is not int:
        L_fault(
            "L5001",
            "`Bytes.slice` takes `int` bounds, found `" + L_kind(end) + "`",
            span,
        )
    length = len(raw)
    s = max(0, min(start, length))
    e = max(s, min(end, length))
    return LBytes(raw[s:e])


def L_bytes_to_array(value: object, span: tuple[int, int, int]) -> list[int]:
    return list(_bytes_receiver(value, "toArray", span).data)


def L_bytes_concat(a: object, b: object, span: tuple[int, int, int]) -> LBytes:
    left = _bytes_receiver(a, "concat", span).data
    right = _bytes_receiver(b, "concat", span).data
    return LBytes(left + right)


def _key(
    value: object,
    span: tuple[int, int, int],
    budget: _StructBudget | None = None,
    depth: int = 0,
) -> object:
    if budget is None:
        budget = _StructBudget()
    budget.consume(depth, span)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is float:
        return ("f64", LFloatKey(L_f64_bits(value), value))
    if isinstance(value, str):
        return ("str", value)
    if value is L_UNIT:
        return ("unit", None)
    if value is L_NULL:
        return ("null", None)
    if value is None:
        return ("none", None)
    if isinstance(value, LBytes):
        return ("bytes", value.data)
    if isinstance(value, Some):
        return ("some", _key(value.value, span, budget, depth + 1))
    if isinstance(value, Ok):
        return ("ok", _key(value.value, span, budget, depth + 1))
    if isinstance(value, Err):
        return ("err", _key(value.value, span, budget, depth + 1))
    if isinstance(value, list):
        return ("list", tuple(_key(item, span, budget, depth + 1) for item in value))
    if _is_langl_newtype(value):
        return ("newtype", value.newtype_id, _key(value.value, span, budget, depth + 1))
    if _is_langl_enum(value):
        if value.enum_id == "RoundingMode":
            L_fault("L5007", "`RoundingMode` values are not comparable", span)
        return (
            "enum",
            value.enum_id,
            value.variant,
            value.variant_index,
            tuple(_key(item, span, budget, depth + 1) for item in value.payloads),
        )
    if isinstance(value, LMap):
        L_fault("L5007", "`Map` values are not comparable", span)
    if isinstance(value, LSet):
        L_fault("L5007", "`Set` values are not comparable", span)
    if isinstance(value, LFile):
        L_fault("L5007", "`File` values are not comparable", span)
    if isinstance(value, LJson):
        L_fault("L5007", "`JSONValue` values are not comparable", span)
    if _is_langl_nominal_record(value):
        fields = []
        for py_field, source_field in value.__langl_record_fields__:
            fields.append(
                (py_field, source_field, _key(getattr(value, py_field), span, budget, depth + 1))
            )
        return ("nominal_record", value.__langl_record_id__, tuple(fields))
    if _is_langl_record(value):
        fields = []
        for py_field, source_field in sorted(
            value.__langl_record_fields__, key=lambda item: item[1]
        ):
            fields.append(
                (py_field, source_field, _key(getattr(value, py_field), span, budget, depth + 1))
            )
        return ("record", tuple(fields))
    L_fault("L5007", "`" + L_kind(value) + "` values are not comparable", span)


def _key_to_value(key: object) -> object:
    tag = key[0]
    value = key[1]
    if tag in ("bool", "int", "f64", "str"):
        if tag == "f64":
            if isinstance(value, LFloatKey):
                return L_f64_from_bits(value.bits)
            return L_f64_from_bits(value)
        return value
    if tag == "unit":
        return L_UNIT
    if tag == "null":
        return L_NULL
    if tag == "none":
        return None
    if tag == "bytes":
        return LBytes(value)
    if tag == "some":
        return Some(_key_to_value(value))
    if tag == "ok":
        return Ok(_key_to_value(value))
    if tag == "err":
        return Err(_key_to_value(value))
    if tag == "list":
        return [_key_to_value(item) for item in value]
    if tag == "newtype":
        return LNewtype(key[1], _key_to_value(key[2]))
    if tag == "enum":
        return LEnum(key[1], key[2], key[3], tuple(_key_to_value(item) for item in key[4]))
    if tag == "record":
        metadata = tuple((py_field, source_field) for py_field, source_field, _ in value)
        values = {
            py_field: _key_to_value(item) for py_field, _source_field, item in value
        }
        return _record_class_for_fields(metadata)(**values)
    if tag == "nominal_record":
        record_id = key[1]
        fields = key[2]
        metadata = tuple((py_field, source_field) for py_field, source_field, _ in fields)
        values = {
            py_field: _key_to_value(item) for py_field, _source_field, item in fields
        }
        return _record_class_for_fields(metadata, record_id)(**values)
    raise TypeError("unknown langl key tag")


def _map_receiver(value: object, name: str, span: tuple[int, int, int]) -> LMap:
    if not isinstance(value, LMap):
        L_fault("L5001", "`Map." + name + "` takes a `Map`, found `" + L_kind(value) + "`", span)
    return value


def _set_receiver(value: object, name: str, span: tuple[int, int, int]) -> LSet:
    if not isinstance(value, LSet):
        L_fault("L5001", "`Set." + name + "` takes a `Set`, found `" + L_kind(value) + "`", span)
    return value


def _map_find(entries: list[tuple[object, object]], key: object) -> int | None:
    for idx, (existing, _) in enumerate(entries):
        if existing == key:
            return idx
    return None


def L_map_new() -> LMap:
    return LMap([])


def L_map_of(pairs: list[tuple[object, object]], span: tuple[int, int, int]) -> LMap:
    out = LMap([])
    for key_value, value in pairs:
        key = _key(key_value, span)
        if _map_find(out.entries, key) is not None:
            L_fault("L4601", "duplicate key in `map { … }` literal", span)
        out.entries.append((key, value))
    return out


_MAP_ENTRY_RECORD_FIELDS = (("_t_6b6579", "key"), ("_t_76616c7565", "value"))


def _map_entry_record(key: object, value: object) -> object:
    cls = _record_class_for_fields(_MAP_ENTRY_RECORD_FIELDS)
    return cls(_t_6b6579=key, _t_76616c7565=value)


def _map_entry_fields(entry: object, span: tuple[int, int, int]) -> tuple[object, object]:
    if not _is_langl_record(entry) or _is_langl_nominal_record(entry):
        L_fault(
            "L5001",
            "`Map.ofEntries` entries must be records `{ key, value }`, found `" + L_kind(entry) + "`",
            span,
        )
    metadata = getattr(entry, "__langl_record_fields__", ())
    fields_by_source = {source_field: py_field for py_field, source_field in metadata}
    if "key" not in fields_by_source or "value" not in fields_by_source:
        L_fault("L5001", "`Map.ofEntries` entries must have `key` and `value` fields", span)
    if len(metadata) != 2:
        L_fault("L5001", "`Map.ofEntries` entries must have exactly `key` and `value` fields", span)
    return getattr(entry, fields_by_source["key"]), getattr(entry, fields_by_source["value"])


def L_map_of_entries(entries: object, span: tuple[int, int, int]) -> LMap:
    if not isinstance(entries, list):
        L_fault(
            "L5001",
            "`Map.ofEntries` takes an `Array` of `{ key, value }` records, found `" + L_kind(entries) + "`",
            span,
        )
    out = LMap([])
    for entry in entries:
        key_value, value = _map_entry_fields(entry, span)
        key = _key(key_value, span)
        idx = _map_find(out.entries, key)
        if idx is None:
            out.entries.append((key, value))
        else:
            out.entries[idx] = (out.entries[idx][0], value)
    return out


def L_map_insert(value: object, key_value: object, item: object, span: tuple[int, int, int]) -> object:
    entries = _map_receiver(value, "insert", span).entries
    key = _key(key_value, span)
    idx = _map_find(entries, key)
    if idx is None:
        entries.append((key, item))
    else:
        entries[idx] = (entries[idx][0], item)
    return L_UNIT


def L_map_get(value: object, key_value: object, span: tuple[int, int, int]) -> Some | None:
    entries = _map_receiver(value, "get", span).entries
    key = _key(key_value, span)
    idx = _map_find(entries, key)
    return Some(entries[idx][1]) if idx is not None else None


def L_map_get_or(value: object, key_value: object, default: object, span: tuple[int, int, int]) -> object:
    found = L_map_get(value, key_value, span)
    return found.value if isinstance(found, Some) else default


def L_map_contains_key(value: object, key_value: object, span: tuple[int, int, int]) -> bool:
    entries = _map_receiver(value, "containsKey", span).entries
    return _map_find(entries, _key(key_value, span)) is not None


def L_map_is_empty(value: object, span: tuple[int, int, int]) -> bool:
    return len(_map_receiver(value, "isEmpty", span).entries) == 0


def L_map_remove(value: object, key_value: object, span: tuple[int, int, int]) -> Some | None:
    entries = _map_receiver(value, "remove", span).entries
    idx = _map_find(entries, _key(key_value, span))
    if idx is None:
        return None
    _, removed = entries.pop(idx)
    return Some(removed)


def L_map_clear(value: object, span: tuple[int, int, int]) -> object:
    _map_receiver(value, "clear", span).entries.clear()
    return L_UNIT


def L_map_map_values(value: object, callback: object, span: tuple[int, int, int]) -> LMap:
    entries = _map_receiver(value, "mapValues", span).entries
    if not callable(callback):
        L_fault("L5001", "`Map.mapValues` callback must be callable", span)
    out = LMap([])
    for key, item in list(entries):
        out.entries.append((key, callback(item)))
    return out


def L_map_map_values__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    entries = _map_receiver(value, "mapValues", span).entries
    if not callable(callback):
        L_fault("L5001", "`Map.mapValues` callback must be callable", span)
    out = LMap([])
    for key, item in list(entries):
        out.entries.append((key, (yield from _L_call_callback_co(callback, (item,), span))))
    return out


def L_map_filter(value: object, callback: object, span: tuple[int, int, int]) -> LMap:
    entries = _map_receiver(value, "filter", span).entries
    if not callable(callback):
        L_fault("L5001", "`Map.filter` callback must be callable", span)
    out = LMap([])
    for key, item in list(entries):
        if L_condition(callback(_key_to_value(key), item), span):
            out.entries.append((key, item))
    return out


def L_map_filter__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    entries = _map_receiver(value, "filter", span).entries
    if not callable(callback):
        L_fault("L5001", "`Map.filter` callback must be callable", span)
    out = LMap([])
    for key, item in list(entries):
        if L_condition((yield from _L_call_callback_co(callback, (_key_to_value(key), item), span)), span):
            out.entries.append((key, item))
    return out


def L_map_update(
    value: object,
    key_value: object,
    initial: object,
    callback: object,
    span: tuple[int, int, int],
) -> object:
    entries = _map_receiver(value, "update", span).entries
    key = _key(key_value, span)
    idx = _map_find(entries, key)
    if idx is None:
        entries.append((key, initial))
        return L_UNIT
    if not callable(callback):
        L_fault("L5001", "`Map.update` callback must be callable", span)
    entries[idx] = (entries[idx][0], callback(entries[idx][1]))
    return L_UNIT


def L_map_update__co(
    value: object,
    key_value: object,
    initial: object,
    callback: object,
    span: tuple[int, int, int],
) -> object:
    entries = _map_receiver(value, "update", span).entries
    key = _key(key_value, span)
    idx = _map_find(entries, key)
    if idx is None:
        entries.append((key, initial))
        return L_UNIT
    if not callable(callback):
        L_fault("L5001", "`Map.update` callback must be callable", span)
    entries[idx] = (entries[idx][0], (yield from _L_call_callback_co(callback, (entries[idx][1],), span)))
    return L_UNIT


def L_set_of(values: list[object], span: tuple[int, int, int]) -> LSet:
    out = LSet([])
    for value in values:
        key = _key(value, span)
        if key not in out.items:
            out.items.append(key)
    return out


def L_set_add(value: object, item: object, span: tuple[int, int, int]) -> object:
    items = _set_receiver(value, "add", span).items
    key = _key(item, span)
    if key not in items:
        items.append(key)
    return L_UNIT


def L_set_remove(value: object, item: object, span: tuple[int, int, int]) -> bool:
    items = _set_receiver(value, "remove", span).items
    key = _key(item, span)
    if key not in items:
        return False
    items.remove(key)
    return True


def L_set_contains(value: object, item: object, span: tuple[int, int, int]) -> bool:
    return _key(item, span) in _set_receiver(value, "contains", span).items


def L_set_is_empty(value: object, span: tuple[int, int, int]) -> bool:
    return len(_set_receiver(value, "isEmpty", span).items) == 0


def L_set_to_array(value: object, span: tuple[int, int, int]) -> list[object]:
    return [_key_to_value(key) for key in _set_receiver(value, "toArray", span).items]


def L_set_union(value: object, other: object, span: tuple[int, int, int]) -> LSet:
    left = _set_receiver(value, "union", span).items
    right = _set_receiver(other, "union", span).items
    out = LSet(list(left))
    for key in right:
        if key not in out.items:
            out.items.append(key)
    return out


def L_set_intersection(value: object, other: object, span: tuple[int, int, int]) -> LSet:
    left = _set_receiver(value, "intersection", span).items
    right = _set_receiver(other, "intersection", span).items
    return LSet([key for key in left if key in right])


def L_set_difference(value: object, other: object, span: tuple[int, int, int]) -> LSet:
    left = _set_receiver(value, "difference", span).items
    right = _set_receiver(other, "difference", span).items
    return LSet([key for key in left if key not in right])


def L_is_empty(value: object, span: tuple[int, int, int]) -> bool:
    if isinstance(value, LBytes):
        return L_bytes_is_empty(value, span)
    if isinstance(value, LMap):
        return L_map_is_empty(value, span)
    if isinstance(value, LSet):
        return L_set_is_empty(value, span)
    L_no_member(value, "isEmpty", span)


def L_to_array(value: object, span: tuple[int, int, int]) -> list[object]:
    if isinstance(value, LBytes):
        return L_bytes_to_array(value, span)
    if isinstance(value, LSet):
        return L_set_to_array(value, span)
    L_no_member(value, "toArray", span)


def L_remove(value: object, item: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, LMap):
        return L_map_remove(value, item, span)
    if isinstance(value, LSet):
        return L_set_remove(value, item, span)
    L_no_member(value, "remove", span)


def L_clear(value: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, list):
        return L_array_clear(value, span)
    if isinstance(value, LMap):
        return L_map_clear(value, span)
    if isinstance(value, LSet):
        value.items.clear()
        return L_UNIT
    L_no_member(value, "clear", span)


def L_member(value: object, py_field: object, source_field: object, span: tuple[int, int, int]) -> object:
    if not isinstance(source_field, str):
        L_fault("L5001", "record field metadata is malformed", span)
    if isinstance(value, list) and source_field == "length":
        return len(value)
    if isinstance(value, LMap):
        if source_field == "keys":
            return [_key_to_value(key) for key, _ in value.entries]
        if source_field == "values":
            return [item for _, item in value.entries]
        if source_field == "entries":
            return [_map_entry_record(_key_to_value(key), item) for key, item in value.entries]
        if source_field == "length":
            return len(value.entries)
    if isinstance(value, LSet) and source_field == "length":
        return len(value.items)
    return L_record_field(value, py_field, source_field, span)


def _wrap_optional(value: object) -> object:
    if isinstance(value, Some) or value is None:
        return value
    return Some(value)


def L_wrap_optional(value: object) -> object:
    return _wrap_optional(value)


def L_wrap_optional_unit(_value: object) -> object:
    return Some(L_UNIT)


def L_optional_member(
    value: object,
    py_field: object,
    source_field: object,
    span: tuple[int, int, int],
) -> object:
    if value is None:
        return None
    if isinstance(value, Some):
        return _wrap_optional(L_member(value.value, py_field, source_field, span))
    return L_member(value, py_field, source_field, span)


class _JsonParseError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


def _json_is_ascii_digit(ch: str | None) -> bool:
    return ch is not None and "0" <= ch <= "9"


class _JsonParser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def peek(self) -> str | None:
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def bump(self) -> str | None:
        ch = self.peek()
        if ch is None:
            return None
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def error(self, message: str) -> _JsonParseError:
        return _JsonParseError(message, self.line, self.column)

    def skip_ws(self) -> None:
        while self.peek() in (" ", "\t", "\n", "\r"):
            self.bump()

    def parse(self) -> LJson:
        self.skip_ws()
        value = self.parse_value(0)
        self.skip_ws()
        if self.peek() is not None:
            raise self.error("unexpected trailing characters after JSON value")
        return value

    def parse_value(self, depth: int) -> LJson:
        if depth > 128:
            raise self.error("JSON nesting exceeds the depth limit")
        ch = self.peek()
        if ch is None:
            raise self.error("unexpected end of input")
        if ch == "n":
            self.parse_lit("null")
            return LJson("null")
        if ch == "t":
            self.parse_lit("true")
            return LJson("bool", True)
        if ch == "f":
            self.parse_lit("false")
            return LJson("bool", False)
        if ch == '"':
            return LJson("string", self.parse_string())
        if ch == "[":
            return self.parse_array(depth)
        if ch == "{":
            return self.parse_object(depth)
        if ch == "-" or _json_is_ascii_digit(ch):
            return self.parse_number()
        raise self.error("unexpected character `" + ch + "`")

    def parse_lit(self, word: str) -> None:
        for expected in word:
            if self.bump() != expected:
                raise self.error("invalid literal, expected `" + word + "`")

    def parse_string(self) -> str:
        self.bump()
        out = []
        while True:
            ch = self.bump()
            if ch is None:
                raise self.error("unterminated string")
            if ch == '"':
                return "".join(out)
            if ch == "\\":
                esc = self.bump()
                if esc == '"':
                    out.append('"')
                elif esc == "\\":
                    out.append("\\")
                elif esc == "/":
                    out.append("/")
                elif esc == "b":
                    out.append("\b")
                elif esc == "f":
                    out.append("\f")
                elif esc == "n":
                    out.append("\n")
                elif esc == "r":
                    out.append("\r")
                elif esc == "t":
                    out.append("\t")
                elif esc == "u":
                    cp = self.parse_hex4()
                    if 0xD800 <= cp <= 0xDBFF:
                        if self.bump() != "\\" or self.bump() != "u":
                            raise self.error("expected a low surrogate")
                        lo = self.parse_hex4()
                        if not (0xDC00 <= lo <= 0xDFFF):
                            raise self.error("invalid low surrogate")
                        out.append(chr(0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)))
                    elif 0xDC00 <= cp <= 0xDFFF:
                        raise self.error("unexpected low surrogate")
                    else:
                        out.append(chr(cp))
                else:
                    raise self.error("invalid string escape")
            elif ord(ch) < 0x20:
                raise self.error("unescaped control character in string")
            else:
                out.append(ch)

    def parse_hex4(self) -> int:
        value = 0
        for _ in range(4):
            ch = self.bump()
            if ch is None or ch.lower() not in "0123456789abcdef":
                raise self.error("invalid \\u escape")
            value = value * 16 + int(ch, 16)
        return value

    def parse_number(self) -> LJson:
        start = self.pos
        if self.peek() == "-":
            self.bump()
        if self.peek() == "0":
            self.bump()
            if _json_is_ascii_digit(self.peek()):
                raise self.error("leading zeros are not allowed")
        elif _json_is_ascii_digit(self.peek()):
            while _json_is_ascii_digit(self.peek()):
                self.bump()
        else:
            raise self.error("invalid number")
        if self.peek() == ".":
            self.bump()
            if not _json_is_ascii_digit(self.peek()):
                raise self.error("expected digits after the decimal point")
            while _json_is_ascii_digit(self.peek()):
                self.bump()
        if self.peek() in ("e", "E"):
            self.bump()
            if self.peek() in ("+", "-"):
                self.bump()
            if not _json_is_ascii_digit(self.peek()):
                raise self.error("expected digits in the exponent")
            while _json_is_ascii_digit(self.peek()):
                self.bump()
        lexeme = self.text[start:self.pos]
        return LJson("number", LJsonNumber(lexeme, _json_exact_int(lexeme)))

    def parse_array(self, depth: int) -> LJson:
        self.bump()
        items = []
        self.skip_ws()
        if self.peek() == "]":
            self.bump()
            return LJson("array", items)
        while True:
            self.skip_ws()
            items.append(self.parse_value(depth + 1))
            self.skip_ws()
            ch = self.bump()
            if ch == "]":
                return LJson("array", items)
            if ch != ",":
                raise self.error("expected `,` or `]` in array")

    def parse_object(self, depth: int) -> LJson:
        self.bump()
        entries = {}
        self.skip_ws()
        if self.peek() == "}":
            self.bump()
            return LJson("object", entries)
        while True:
            self.skip_ws()
            if self.peek() != '"':
                raise self.error("expected a string key in object")
            key = self.parse_string()
            self.skip_ws()
            if self.bump() != ":":
                raise self.error("expected `:` after the object key")
            self.skip_ws()
            value = self.parse_value(depth + 1)
            if key in entries:
                raise self.error("duplicate object key")
            entries[key] = value
            self.skip_ws()
            ch = self.bump()
            if ch == "}":
                return LJson("object", dict(sorted(entries.items())))
            if ch != ",":
                raise self.error("expected `,` or `}` in object")


class _JsonStringifyError(Exception):
    pass


def _json_exact_int(lexeme: str) -> int | None:
    neg = lexeme.startswith("-")
    body = lexeme[1:] if neg else lexeme
    if "e" in body or "E" in body:
        body, exp_text = body.replace("E", "e").split("e", 1)
        try:
            exp = int(exp_text)
        except ValueError:
            return None
        if exp < I128_MIN or exp > I128_MAX:
            return None
    else:
        exp = 0
    if "." in body:
        whole, frac = body.split(".", 1)
    else:
        whole, frac = body, ""

    digits = (whole + frac).lstrip("0")
    if digits == "":
        return 0

    shift = exp - len(frac)
    if shift >= 0:
        if len(digits) + shift > 19:
            return None
        digits = digits + ("0" * shift)
    elif shift <= -len(digits):
        return None
    else:
        drop = -shift
        keep, dropped = digits[:-drop], digits[-drop:]
        if any(ch != "0" for ch in dropped):
            return None
        digits = keep

    if len(digits) > 19:
        return None
    try:
        value = int(("-" if neg else "") + digits)
    except ValueError:
        return None
    if value < INT_MIN or value > INT_MAX:
        return None
    return value


def _json_escape(raw: str) -> str:
    out = ['"']
    for ch in raw:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _parse_extern_sandbox_policies(text: str | None) -> dict[str, ExternSandboxPolicy] | None:
    if text is None or text == "":
        return None
    try:
        node = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "extern sandbox policies JSON is invalid at line "
            + str(error.lineno)
            + ", column "
            + str(error.colno)
            + ": "
            + error.msg
        ) from None
    if not isinstance(node, list):
        raise ValueError("extern sandbox policies must be an array")
    policies: dict[str, ExternSandboxPolicy] = {}
    for index, item in enumerate(node):
        path = "extern sandbox policies[" + str(index) + "]"
        if not isinstance(item, dict):
            raise ValueError(path + " must be an object")
        _abi_exact_fields(item, {"module", "kind", "artifact_path", "fuel", "memory_bytes"}, path)
        module = item["module"]
        kind = item["kind"]
        artifact_path = item["artifact_path"]
        fuel = item["fuel"]
        memory_bytes = item["memory_bytes"]
        if not isinstance(module, str) or module == "":
            raise ValueError(path + ".module must be a non-empty string")
        if kind not in ("replay", "wasm"):
            raise ValueError(path + ".kind must be `replay` or `wasm`")
        if artifact_path is not None and not isinstance(artifact_path, str):
            raise ValueError(path + ".artifact_path must be a string or null")
        fuel = _parse_optional_u64(fuel, path + ".fuel")
        memory_bytes = _parse_optional_u64(memory_bytes, path + ".memory_bytes")
        policy = ExternSandboxPolicy(module, kind, artifact_path, fuel, memory_bytes)
        _validate_extern_sandbox_policy(policy)
        if module in policies:
            raise ValueError("extern sandbox policy declares a duplicate module")
        policies[module] = policy
    return policies


def _parse_optional_u64(value: object, path: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0 or value > U64_MAX:
        raise ValueError(path + " must be a u64 integer or null")
    return value


def _validate_extern_sandbox_policy(policy: ExternSandboxPolicy) -> None:
    if policy.module == "":
        raise ValueError("extern sandbox policy module must not be empty")
    if policy.kind == "wasm" and policy.artifact_path is None:
        raise ValueError(
            "extern sandbox policy for `" + policy.module + "` kind `wasm` requires an artifact"
        )


def _enforce_extern_replay_budget(
    policy: ExternSandboxPolicy,
    module: str,
    function: str,
    args: tuple[object, ...],
    args_json: str,
    result: object,
) -> None:
    if policy.fuel is not None:
        used = _extern_replay_fuel_used(args, result)
        if used > policy.fuel:
            raise ValueError(
                "extern replay fuel limit exceeded for `"
                + module
                + "."
                + function
                + "`: used "
                + str(used)
                + ", budget "
                + str(policy.fuel)
            )
    if policy.memory_bytes is not None:
        result_json = _abi_encode_value(result, "$", 0)
        used = _extern_replay_memory_bytes_used(args_json, result_json)
        if used > policy.memory_bytes:
            raise ValueError(
                "extern replay memory_bytes limit exceeded for `"
                + module
                + "."
                + function
                + "`: used "
                + str(used)
                + ", budget "
                + str(policy.memory_bytes)
            )


def _extern_replay_fuel_used(args: tuple[object, ...], result: object) -> int:
    used = 1
    for arg in args:
        used = _abi_charge_add(used, _abi_value_nodes(arg, 0))
    return _abi_charge_add(used, _abi_value_nodes(result, 0))


def _extern_replay_memory_bytes_used(args_json: str, result_json: str) -> int:
    return _abi_charge_add(len(args_json.encode("utf-8")), len(result_json.encode("utf-8")))


def _abi_value_nodes(value: object, depth: int) -> int:
    if depth > 128:
        raise ValueError("ABI_LIMIT: extern replay resource envelope exceeds the ABI value depth limit")
    child_depth = depth + 1
    total = 1
    if isinstance(value, (Some, Ok, Err)):
        return _abi_charge_add(total, _abi_value_nodes(value.value, child_depth))
    if isinstance(value, list):
        for item in value:
            total = _abi_charge_add(total, _abi_value_nodes(item, child_depth))
        return total
    if _is_langl_record(value):
        for py_field, _source_field in getattr(value, "__langl_record_fields__"):
            total = _abi_charge_add(total, _abi_value_nodes(getattr(value, py_field), child_depth))
        return total
    if (
        type(value) is int
        or type(value) is bool
        or isinstance(value, str)
        or value is L_UNIT
        or value is L_NULL
        or value is None
        or isinstance(value, LJson)
        or isinstance(value, LBytes)
    ):
        return total
    raise ValueError("ABI_UNSUPPORTED: extern replay resource envelope contains `" + L_kind(value) + "`")


def _abi_charge_add(lhs: int, rhs: int) -> int:
    total = lhs + rhs
    if total > U64_MAX:
        raise ValueError("extern replay resource envelope exceeds u64")
    return total


def _mangle(name: str) -> str:
    return "_t_" + "".join(format(byte, "02x") for byte in name.encode("utf-8"))


def _abi_encode_value(value: object, path: str, depth: int) -> str:
    if depth > 128:
        raise ValueError("ABI_LIMIT: " + path + ": structure exceeds the ABI value depth limit")
    if type(value) is int:
        return '{"$":"int","value":' + _json_escape(str(value)) + "}"
    if type(value) is bool:
        return '{"$":"bool","value":' + ("true" if value else "false") + "}"
    if isinstance(value, str):
        return '{"$":"string","value":' + _json_escape(value) + "}"
    if value is L_UNIT:
        return '{"$":"unit"}'
    if value is L_NULL:
        return '{"$":"null"}'
    if value is None:
        return '{"$":"none"}'
    if isinstance(value, Some):
        return '{"$":"some","value":' + _abi_encode_value(value.value, path + ".value", depth + 1) + "}"
    if isinstance(value, Ok):
        return '{"$":"ok","value":' + _abi_encode_value(value.value, path + ".value", depth + 1) + "}"
    if isinstance(value, Err):
        return '{"$":"err","value":' + _abi_encode_value(value.value, path + ".value", depth + 1) + "}"
    if isinstance(value, list):
        return (
            '{"$":"array","items":['
            + ",".join(_abi_encode_value(item, path + ".items[" + str(i) + "]", depth + 1) for i, item in enumerate(value))
            + "]}"
        )
    if isinstance(value, LBytes):
        return '{"$":"bytes","hex":' + _json_escape(L_bytes_to_hex(value)) + "}"
    if isinstance(value, LJson):
        return '{"$":"json","value":' + _json_write_node(value) + "}"
    if _is_langl_newtype(value):
        return (
            '{"$":"newtype","id":'
            + _json_escape(value.newtype_id)
            + ',"value":'
            + _abi_encode_value(value.value, path + ".value", depth + 1)
            + "}"
        )
    if _is_langl_record(value):
        fields = []
        for py_name, source_name in sorted(getattr(value, "__langl_record_fields__"), key=lambda item: item[1]):
            fields.append(_json_escape(source_name) + ":" + _abi_encode_value(getattr(value, py_name), path + ".fields." + source_name, depth + 1))
        if getattr(value, "__langl_record_id__", None) is not None:
            ordered = []
            for py_name, source_name in getattr(value, "__langl_record_fields__"):
                ordered.append(
                    '{"name":'
                    + _json_escape(source_name)
                    + ',"value":'
                    + _abi_encode_value(getattr(value, py_name), path + ".fields." + source_name, depth + 1)
                    + "}"
                )
            return (
                '{"$":"nominal-record","id":'
                + _json_escape(value.__langl_record_id__)
                + ',"fields":['
                + ",".join(ordered)
                + "]}"
            )
        return '{"$":"record","fields":{' + ",".join(fields) + "}}"
    raise ValueError("ABI_UNSUPPORTED: " + path + ": `" + L_kind(value) + "` is not ABI-encodable in PW0")


def _abi_args_encode(args: tuple[object, ...]) -> str:
    return "[" + ",".join(_abi_encode_value(arg, "$[" + str(i) + "]", 0) for i, arg in enumerate(args)) + "]"


def _abi_exact_fields(node: dict[str, object], fields: set[str], path: str) -> None:
    actual = set(node.keys())
    if actual != fields:
        raise ValueError(
            "ABI_FIELDS: "
            + path
            + " expected fields "
            + ", ".join(sorted(fields))
            + ", got "
            + ", ".join(sorted(actual))
        )


def _abi_decode_value(node: object, path: str, depth: int) -> object:
    if depth > 128:
        raise ValueError("ABI_LIMIT: " + path + ": structure exceeds the ABI value depth limit")
    if not isinstance(node, dict):
        raise ValueError("ABI_SHAPE: " + path + " must be an object")
    tag = node.get("$")
    if not isinstance(tag, str):
        raise ValueError("ABI_TAG: " + path + ".$ must be a string")
    if tag == "int":
        _abi_exact_fields(node, {"$", "value"}, path)
        raw = node["value"]
        if not isinstance(raw, str):
            raise ValueError("ABI_INT: " + path + ".value must be a string")
        try:
            value = int(raw, 10)
        except ValueError:
            raise ValueError("ABI_INT: " + path + ".value is not an i64 decimal string") from None
        if str(value) != raw or value < INT_MIN or value > INT_MAX:
            raise ValueError("ABI_INT: " + path + ".value is not canonical decimal")
        return value
    if tag == "bool":
        _abi_exact_fields(node, {"$", "value"}, path)
        value = node["value"]
        if type(value) is not bool:
            raise ValueError("ABI_BOOL: " + path + ".value must be boolean")
        return value
    if tag == "string":
        _abi_exact_fields(node, {"$", "value"}, path)
        value = node["value"]
        if not isinstance(value, str):
            raise ValueError("ABI_STRING: " + path + ".value must be a string")
        return value
    if tag == "unit":
        _abi_exact_fields(node, {"$"}, path)
        return L_UNIT
    if tag == "null":
        _abi_exact_fields(node, {"$"}, path)
        return L_NULL
    if tag == "none":
        _abi_exact_fields(node, {"$"}, path)
        return None
    if tag == "some":
        _abi_exact_fields(node, {"$", "value"}, path)
        return Some(_abi_decode_value(node["value"], path + ".value", depth + 1))
    if tag == "ok":
        _abi_exact_fields(node, {"$", "value"}, path)
        return Ok(_abi_decode_value(node["value"], path + ".value", depth + 1))
    if tag == "err":
        _abi_exact_fields(node, {"$", "value"}, path)
        return Err(_abi_decode_value(node["value"], path + ".value", depth + 1))
    if tag == "array":
        _abi_exact_fields(node, {"$", "items"}, path)
        items = node["items"]
        if not isinstance(items, list):
            raise ValueError("ABI_ARRAY: " + path + ".items must be an array")
        return [_abi_decode_value(item, path + ".items[" + str(i) + "]", depth + 1) for i, item in enumerate(items)]
    if tag == "record":
        _abi_exact_fields(node, {"$", "fields"}, path)
        fields = node["fields"]
        if not isinstance(fields, dict):
            raise ValueError("ABI_RECORD: " + path + ".fields must be an object")
        metadata = tuple((_mangle(source_name), source_name) for source_name in sorted(fields.keys()))
        values = {
            py_field: _abi_decode_value(fields[source_name], path + ".fields." + source_name, depth + 1)
            for py_field, source_name in metadata
        }
        return _record_class_for_fields(metadata)(**values)
    if tag == "nominal-record":
        _abi_exact_fields(node, {"$", "id", "fields"}, path)
        record_id = node["id"]
        fields = node["fields"]
        if not isinstance(record_id, str):
            raise ValueError("ABI_NOMINAL_RECORD: " + path + ".id must be a string")
        if not isinstance(fields, list):
            raise ValueError("ABI_NOMINAL_RECORD: " + path + ".fields must be an array")
        seen: set[str] = set()
        metadata = []
        values = {}
        for i, field in enumerate(fields):
            field_path = path + ".fields[" + str(i) + "]"
            if not isinstance(field, dict):
                raise ValueError("ABI_NOMINAL_RECORD: " + field_path + " must be an object")
            _abi_exact_fields(field, {"name", "value"}, field_path)
            source_name = field["name"]
            if not isinstance(source_name, str):
                raise ValueError("ABI_NOMINAL_RECORD: " + field_path + ".name must be a string")
            if source_name in seen:
                raise ValueError("ABI_NOMINAL_RECORD: " + field_path + ".name duplicates `" + source_name + "`")
            seen.add(source_name)
            py_field = _mangle(source_name)
            metadata.append((py_field, source_name))
            values[py_field] = _abi_decode_value(field["value"], field_path + ".value", depth + 1)
        return _record_class_for_fields(tuple(metadata), record_id)(**values)
    if tag == "newtype":
        _abi_exact_fields(node, {"$", "id", "value"}, path)
        newtype_id = node["id"]
        if not isinstance(newtype_id, str):
            raise ValueError("ABI_NEWTYPE: " + path + ".id must be a string")
        return LNewtype(newtype_id, _abi_decode_value(node["value"], path + ".value", depth + 1))
    if tag == "bytes":
        _abi_exact_fields(node, {"$", "hex"}, path)
        raw = node["hex"]
        if not isinstance(raw, str):
            raise ValueError("ABI_BYTES: " + path + ".hex must be a string")
        decoded = L_bytes_from_hex(raw, (0, 0, 0))
        if isinstance(decoded, Err):
            raise ValueError("ABI_BYTES: " + path + ".hex is not lowercase hex")
        if L_bytes_to_hex(decoded.value) != raw:
            raise ValueError("ABI_BYTES: " + path + ".hex is non-lowercase-hex")
        return decoded.value
    if tag == "json":
        _abi_exact_fields(node, {"$", "value"}, path)
        return _json_to_L_json(node["value"], path + ".value", depth + 1)
    raise ValueError("ABI_TAG: " + path + " has unsupported tag `" + tag + "`")


def _json_to_L_json(node: object, path: str, depth: int) -> LJson:
    if depth > 128:
        raise ValueError("ABI_LIMIT: " + path + ": structure exceeds the ABI value depth limit")
    if node is None:
        return LJson("null")
    if type(node) is bool:
        return LJson("bool", node)
    if isinstance(node, str):
        return LJson("string", node)
    if type(node) is int:
        return LJson("number", LJsonNumber(str(node), node))
    if isinstance(node, list):
        return LJson("array", [_json_to_L_json(item, path + "[" + str(i) + "]", depth + 1) for i, item in enumerate(node)])
    if isinstance(node, dict):
        return LJson("object", {key: _json_to_L_json(value, path + "." + key, depth + 1) for key, value in sorted(node.items())})
    raise ValueError("ABI_JSON: " + path + " has unsupported JSON value")


def _json_write_node(node: LJson) -> str:
    if node.kind == "null":
        return "null"
    if node.kind == "bool":
        return "true" if node.value else "false"
    if node.kind == "string":
        return _json_escape(node.value)
    if node.kind == "number":
        return node.value.lexeme
    if node.kind == "array":
        return "[" + ",".join(_json_write_node(item) for item in node.value) + "]"
    if node.kind == "object":
        return "{" + ",".join(_json_escape(k) + ":" + _json_write_node(v) for k, v in sorted(node.value.items())) + "}"
    raise TypeError("unknown JSON node")


def _json_encode_value(value: object, path: str, depth: int) -> str:
    if depth > 128:
        raise _JsonStringifyError(
            "JSON_LIMIT: " + path + ": structure exceeds the JSON.stringify depth limit"
        )
    if isinstance(value, LJson):
        return _json_write_node(value)
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if value is L_UNIT or value is L_NULL or value is None:
        return "null"
    if isinstance(value, str):
        return _json_escape(value)
    if isinstance(value, Some):
        return _json_encode_value(value.value, path, depth)
    if isinstance(value, list):
        return "[" + ",".join(_json_encode_value(item, path + "[" + str(i) + "]", depth + 1) for i, item in enumerate(value)) + "]"
    if type(value) is float:
        raise _JsonStringifyError(
            "JSON_UNSUPPORTED: " + path + ": float is not supported by JSON.stringify v1"
        )
    raise _JsonStringifyError(
        "JSON_UNSUPPORTED: " + path + ": `" + L_kind(value) + "` is not JSON-encodable"
    )


def L_json_parse(text: object, span: tuple[int, int, int]) -> Ok | Err:
    if not isinstance(text, str):
        L_fault("L5001", "`JSON.parse` takes a string; got `" + L_kind(text) + "` (§22)", span)
    try:
        return Ok(_JsonParser(text).parse())
    except _JsonParseError as error:
        return Err(LJsonParseErrorRecord(error.column, error.line, error.message))


def L_json_stringify(value: object) -> Ok | Err:
    try:
        return Ok(_json_encode_value(value, "$", 0))
    except _JsonStringifyError as error:
        return Err(str(error))


def _json_receiver(value: object, member: str, span: tuple[int, int, int]) -> LJson:
    if not isinstance(value, LJson):
        L_no_member(value, member, span)
    return value


def L_json_kind(value: object, span: tuple[int, int, int]) -> str:
    return _json_receiver(value, "kind", span).kind


def L_json_is_null(value: object, span: tuple[int, int, int]) -> bool:
    return _json_receiver(value, "isNull", span).kind == "null"


def L_json_as_string(value: object, span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "asString", span)
    return Some(node.value) if node.kind == "string" else None


def L_json_as_bool(value: object, span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "asBool", span)
    return Some(node.value) if node.kind == "bool" else None


def L_json_as_int(value: object, span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "asInt", span)
    if node.kind == "number" and node.value.int_value is not None:
        return Some(node.value.int_value)
    return None


def L_json_number_text(value: object, span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "numberText", span)
    return Some(node.value.lexeme) if node.kind == "number" else None


def L_json_get(value: object, key: object, member_span: tuple[int, int, int], call_span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "get", member_span)
    if node.kind != "object":
        return None
    if not isinstance(key, str):
        L_fault("L5001", "`JSONValue.get` takes a string key; got `" + L_kind(key) + "`", call_span)
    return Some(node.value[key]) if key in node.value else None


def L_get(value: object, key: object, span: tuple[int, int, int]) -> Some | None:
    if isinstance(value, LJson):
        return L_json_get(value, key, span, span)
    if isinstance(value, LBytes):
        return L_bytes_get(value, key, span)
    if isinstance(value, LMap):
        return L_map_get(value, key, span)
    return L_array_get(value, key, span)


def L_json_at(value: object, index: object, member_span: tuple[int, int, int], call_span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "at", member_span)
    if node.kind != "array":
        return None
    idx = _int(index, call_span)
    return Some(node.value[idx]) if 0 <= idx < len(node.value) else None


def L_json_length(value: object, span: tuple[int, int, int]) -> Some | None:
    node = _json_receiver(value, "length", span)
    if node.kind in ("array", "object"):
        return Some(len(node.value))
    return None


def L_length(value: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, LJson):
        return L_json_length(value, span)
    if isinstance(value, LBytes):
        return L_bytes_length(value, span)
    L_no_member(value, "length", span)


def L_kind(value: object) -> str:
    if type(value) is bool:
        return "bool"
    if type(value) is int:
        return "int"
    if type(value) is float:
        return "float"
    if isinstance(value, str):
        return "string"
    if value is L_UNIT:
        return "()"
    if value is L_NULL:
        return "null"
    if value is None:
        return "Option"
    if isinstance(value, Some):
        return "Option"
    if isinstance(value, (Ok, Err)):
        return "Result"
    if isinstance(value, list):
        return "Array"
    if isinstance(value, LFile):
        return "File"
    if isinstance(value, LBytes):
        return "Bytes"
    if isinstance(value, LMap):
        return "Map"
    if isinstance(value, LSet):
        return "Set"
    if isinstance(value, LRange):
        return "range"
    if isinstance(value, LComposed):
        return "function"
    if isinstance(value, LHostCallable):
        return "function"
    if isinstance(value, LExternFunction):
        return "function"
    if isinstance(value, LJson):
        return "JSONValue"
    if _is_langl_enum(value):
        return "enum"
    if _is_langl_newtype(value):
        return "newtype"
    if _is_langl_record(value):
        return "record"
    return "unknown"


def L_impossible_match(value: object, span: tuple[int, int, int]) -> object:
    L_fault("L5001", "non-exhaustive match reached generated fallback", span)


def L_return(value: object) -> object:
    raise LReturn(value)


def L_record_field(value: object, py_field: object, source_field: object, span: tuple[int, int, int]) -> object:
    if not isinstance(py_field, str) or not isinstance(source_field, str):
        L_fault("L5001", "record field metadata is malformed", span)
    if not hasattr(value, py_field):
        record_id = getattr(value, "__langl_record_id__", None)
        if isinstance(record_id, str):
            L_fault("L5006", "record `" + record_id + "` has no field `" + source_field + "`", span)
        L_fault("L5001", "record has no field `" + source_field + "`", span)
    return getattr(value, py_field)


def _is_langl_record(value: object) -> bool:
    return isinstance(getattr(value, "__langl_record_fields__", None), tuple)


def _is_langl_nominal_record(value: object) -> bool:
    return _is_langl_record(value) and isinstance(getattr(value, "__langl_record_id__", None), str)


def _is_langl_newtype(value: object) -> bool:
    return isinstance(value, LNewtype)


def _is_langl_enum(value: object) -> bool:
    return isinstance(value, LEnum)


def L_newtype(newtype_id: object, value: object, span: tuple[int, int, int]) -> LNewtype:
    if not isinstance(newtype_id, str):
        L_fault("L5001", "newtype metadata is malformed", span)
    return LNewtype(newtype_id, value)


def L_is_newtype(value: object, newtype_id: object) -> bool:
    return isinstance(newtype_id, str) and _is_langl_newtype(value) and value.newtype_id == newtype_id


def L_newtype_unwrap(value: object, span: tuple[int, int, int]) -> object:
    if _is_langl_newtype(value):
        return value.value
    L_fault("L5001", "`.value()` needs a newtype, found a " + L_kind(value), span)


def L_enum(
    enum_id: object,
    variant: object,
    variant_index: object,
    payloads: object,
    span: tuple[int, int, int],
) -> LEnum:
    if not isinstance(enum_id, str) or not isinstance(variant, str) or type(variant_index) is not int:
        L_fault("L5001", "enum metadata is malformed", span)
    if not isinstance(payloads, list):
        L_fault("L5001", "enum payload metadata is malformed", span)
    return LEnum(enum_id, variant, variant_index, tuple(payloads))


def L_is_enum(value: object, enum_ids: object, variant: object, arity: object) -> bool:
    if not _is_langl_enum(value) or not isinstance(enum_ids, tuple) or not isinstance(variant, str):
        return False
    if value.enum_id not in enum_ids or value.variant != variant:
        return False
    return arity is None or len(value.payloads) == arity


def L_enum_bare_variant_matches(value: object, enum_ids: object, variant: object) -> bool:
    if not isinstance(enum_ids, tuple) or not isinstance(variant, str):
        return False
    if _is_langl_enum(value) and value.enum_id in enum_ids:
        return value.variant == variant
    return True


def L_enum_bare_variant_binds(value: object, enum_ids: object) -> bool:
    return not (_is_langl_enum(value) and isinstance(enum_ids, tuple) and value.enum_id in enum_ids)


def L_enum_pattern(
    value: object,
    enum_ids: object,
    variant: object,
    arity: object,
    span: tuple[int, int, int],
) -> bool:
    if not isinstance(arity, int):
        L_fault("L5001", "enum pattern metadata is malformed", span)
    if not _is_langl_enum(value) or not isinstance(enum_ids, tuple) or not isinstance(variant, str):
        return False
    if value.enum_id not in enum_ids or value.variant != variant:
        return False
    if len(value.payloads) != arity:
        L_fault(
            "L5001",
            "enum variant `" + variant + "` pattern takes "
            + str(len(value.payloads))
            + " subpattern"
            + ("" if len(value.payloads) == 1 else "s"),
            span,
        )
    return True


def L_type_matches(value: object, spec: object) -> bool:
    return _L_type_matches(value, spec, {})


def _L_python_callable_arity(value: object, skip_first: int = 0) -> tuple[int, int | None] | None:
    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        return (0, None) if callable(value) else None
    required = 0
    fixed = 0
    variadic = False
    for param in signature.parameters.values():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            fixed += 1
            if param.default is inspect.Parameter.empty:
                required += 1
        elif param.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic = True
    if skip_first:
        skipped = min(skip_first, fixed)
        fixed -= skipped
        required = max(0, required - skipped)
    return required, None if variadic else fixed


def _L_callable_arity(value: object) -> tuple[int, int | None] | None:
    if isinstance(value, LComposed):
        return _L_callable_arity(value.first)
    if isinstance(value, LHostCallable):
        minimum, maximum = _L_python_callable_arity(value.fn, 1)
        if value.variadic_py_name is not None:
            return minimum, None
        return minimum, maximum
    if isinstance(value, LExternFunction):
        return (0, None)
    return _L_python_callable_arity(value)


def _L_callable_shape_matches(value: object, n_fixed: int, type_variadic: bool) -> bool:
    arity = _L_callable_arity(value)
    if arity is None:
        return False
    minimum, maximum = arity
    if type_variadic:
        return maximum is None and minimum <= n_fixed
    return minimum <= n_fixed and (maximum is None or n_fixed <= maximum)


def _L_type_matches(value: object, spec: object, refs: dict[str, object]) -> bool:
    if spec == "int":
        return type(value) is int
    if spec == "float":
        return type(value) is float
    if spec == "string":
        return isinstance(value, str)
    if spec == "bool":
        return type(value) is bool
    if spec == "JSONValue":
        return isinstance(value, LJson)
    if spec == "Bytes":
        return isinstance(value, LBytes)
    if not isinstance(spec, tuple) or len(spec) == 0:
        return False

    tag = spec[0]
    if tag == "type_ref":
        if len(spec) != 2 or not isinstance(spec[1], str):
            return False
        target = refs.get(spec[1])
        return target is not None and _L_type_matches(value, target, refs)
    if tag == "union":
        return any(_L_type_matches(value, member, refs) for member in spec[1])
    if tag == "option":
        return value is None or (
            isinstance(value, Some) and _L_type_matches(value.value, spec[1], refs)
        )
    if tag == "result":
        return (
            isinstance(value, Ok)
            and _L_type_matches(value.value, spec[1], refs)
        ) or (
            isinstance(value, Err)
            and _L_type_matches(value.value, spec[2], refs)
        )
    if tag == "array":
        return isinstance(value, list) and all(_L_type_matches(item, spec[1], refs) for item in value)
    if tag == "set":
        return isinstance(value, LSet) and all(
            _L_type_matches(_key_to_value(item), spec[1], refs) for item in value.items
        )
    if tag == "map":
        return isinstance(value, LMap) and all(
            _L_type_matches(_key_to_value(key), spec[1], refs) and _L_type_matches(item, spec[2], refs)
            for key, item in value.entries
        )
    if tag == "function":
        return (
            len(spec) == 3
            and isinstance(spec[1], int)
            and type(spec[2]) is bool
            and _L_callable_shape_matches(value, spec[1], spec[2])
        )
    if tag == "record":
        if not _is_langl_record(value) or _is_langl_nominal_record(value):
            return False
        fields = spec[1]
        actual = getattr(value, "__langl_record_fields__", ())
        if len(actual) != len(fields):
            return False
        actual_by_source = {source: py for py, source in actual}
        for source_field, py_field, field_spec in fields:
            if actual_by_source.get(source_field) != py_field:
                return False
            if not _L_type_matches(getattr(value, py_field), field_spec, refs):
                return False
        return True
    if tag == "nominal_record":
        if not _is_langl_nominal_record(value) or value.__langl_record_id__ != spec[1]:
            return False
        if len(spec) == 2:
            return True
        fields = spec[2]
        actual = getattr(value, "__langl_record_fields__", ())
        actual_by_source = {source: py for py, source in actual}
        for source_field, py_field, field_spec in fields:
            if actual_by_source.get(source_field) != py_field:
                return False
            if not hasattr(value, py_field):
                return False
            if not _L_type_matches(getattr(value, py_field), field_spec, refs):
                return False
        return True
    if tag == "newtype":
        return len(spec) == 2 and _is_langl_newtype(value) and value.newtype_id == spec[1]
    if tag == "enum":
        if not _is_langl_enum(value) or value.enum_id != spec[1]:
            return False
        if len(spec) == 2:
            return True
        if len(spec) == 3:
            variants = spec[2]
            ref_key = None
        elif len(spec) == 4:
            if not isinstance(spec[2], str):
                return False
            ref_key = spec[2]
            variants = spec[3]
        else:
            return False
        if not isinstance(variants, tuple):
            return False
        old_ref = refs.get(ref_key) if ref_key is not None else None
        if ref_key is not None:
            refs[ref_key] = spec
        for variant_spec in variants:
            if not isinstance(variant_spec, tuple) or len(variant_spec) != 2:
                if ref_key is not None:
                    if old_ref is None:
                        refs.pop(ref_key, None)
                    else:
                        refs[ref_key] = old_ref
                return False
            variant_name, payload_specs = variant_spec
            if variant_name != value.variant:
                continue
            if not isinstance(payload_specs, tuple) or len(payload_specs) != len(value.payloads):
                if ref_key is not None:
                    if old_ref is None:
                        refs.pop(ref_key, None)
                    else:
                        refs[ref_key] = old_ref
                return False
            matched = all(
                _L_type_matches(payload, payload_spec, refs)
                for payload, payload_spec in zip(value.payloads, payload_specs)
            )
            if ref_key is not None:
                if old_ref is None:
                    refs.pop(ref_key, None)
                else:
                    refs[ref_key] = old_ref
            return matched
        if ref_key is not None:
            if old_ref is None:
                refs.pop(ref_key, None)
            else:
                refs[ref_key] = old_ref
        return False
    return False


def _record_class_for_fields(fields: tuple[tuple[str, str], ...], record_id: str | None = None) -> type:
    key = (record_id, fields)
    cached = _RECORD_CLASS_CACHE.get(key)
    if cached is not None:
        return cached
    namespace: dict[str, object] = {"__langl_record_fields__": fields}
    if record_id is not None:
        namespace["__langl_record_id__"] = record_id
    cls = make_dataclass(
        "langlRecord" + str(len(_RECORD_CLASS_CACHE)),
        [(py_field, object) for py_field, _ in fields],
        frozen=True,
        slots=True,
        namespace=namespace,
    )
    _RECORD_CLASS_CACHE[key] = cls
    return cls


def L_nominal_record(
    record_type: type,
    record_id: str,
    decl_fields: list[tuple[str, str, object]],
    spread,
    fields: list[tuple[str, str, object]],
    span: tuple[int, int, int],
) -> object:
    decl_by_py: dict[str, tuple[str, object]] = {}
    for py_field, source_field, default in decl_fields:
        if not isinstance(py_field, str) or not isinstance(source_field, str):
            L_fault("L5001", "nominal record metadata is malformed", span)
        decl_by_py[py_field] = (source_field, default)
    seen: set[str] = set()
    for py_field, source_field, _thunk in fields:
        if not isinstance(py_field, str) or not isinstance(source_field, str):
            L_fault("L5001", "nominal record field metadata is malformed", span)
        if py_field not in decl_by_py:
            L_fault("L5006", "record `" + record_id + "` has no field `" + source_field + "`", span)
        if py_field in seen:
            L_fault("L5004", "field `" + source_field + "` is given twice in `" + record_id + "`", span)
        seen.add(py_field)

    values: dict[str, object] = {}
    if spread is not None:
        base = spread()
        if _is_langl_nominal_record(base) and base.__langl_record_id__ != record_id:
            L_fault(
                "L5001",
                "record spread `...` needs a `" + record_id + "`, found a `" + base.__langl_record_id__ + "`",
                span,
            )
        if not _is_langl_nominal_record(base):
            L_fault(
                "L5001",
                "record spread `...` needs a `" + record_id + "`, found a " + L_kind(base),
                span,
            )
        for py_field, _source_field, _default in decl_fields:
            values[py_field] = getattr(base, py_field)

    for py_field, _source_field, thunk in fields:
        values[py_field] = thunk()

    for py_field, source_field, default in decl_fields:
        if py_field in values:
            continue
        if default is None:
            L_fault("L5004", "record `" + record_id + "` is missing field `" + source_field + "`", span)
        values[py_field] = default()
    return record_type(**values)


def L_record_update(base: object, fields: list[tuple[str, str, object]], span: tuple[int, int, int]) -> object:
    if not _is_langl_record(base):
        L_fault("L5001", "record update needs a record, found `" + L_kind(base) + "`", span)
    values = {py_field: getattr(base, py_field) for py_field, _ in base.__langl_record_fields__}
    field_names = {py_field: source_field for py_field, source_field in base.__langl_record_fields__}
    evaluated: list[tuple[str, str, object]] = []
    for py_field, source_field, thunk in fields:
        if not isinstance(py_field, str) or not isinstance(source_field, str):
            L_fault("L5001", "record update metadata is malformed", span)
        evaluated.append((py_field, source_field, thunk()))
    updating = len(values)
    for py_field, source_field, value in evaluated:
        if updating > 0 and py_field not in values:
            L_fault("L5006", "record update names unknown field `" + source_field + "`", span)
        values[py_field] = value
        field_names[py_field] = source_field
    if updating == 0 and values:
        metadata = tuple((py_field, field_names[py_field]) for py_field in values)
        return _record_class_for_fields(metadata)(**values)
    return type(base)(**values)


def _int(value: object, span: tuple[int, int, int]) -> int:
    if type(value) is not int:
        L_fault("L5001", "expected `int`", span)
    return value


def L_range(
    lo: object,
    hi: object,
    inclusive: bool,
    step: object | None,
    span: tuple[int, int, int],
) -> LRange:
    if type(lo) is not int or type(hi) is not int:
        L_fault("L5001", "range endpoints must be `int` in this build (§10)", span)
    if step is None:
        step_value = 1
    elif type(step) is int:
        if step == 0:
            L_fault("L4003", "range step must not be zero (§10)", span)
        step_value = step
    else:
        L_fault(
            "L5001",
            "range step must be `int`, found `" + L_kind(step) + "`",
            span,
        )
    return LRange(lo, hi, inclusive, step_value)


def _check_i64(value: int, span: tuple[int, int, int], message: str) -> int:
    if value < INT_MIN or value > INT_MAX:
        L_fault("L4004", message, span)
    return value


def L_i64(value: object, span: tuple[int, int, int]) -> int:
    return _check_i64(_int(value, span), span, "integer value is outside i64 range")


def L_add_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    return _check_i64(_int(a, span) + _int(b, span), span, "integer addition overflows")


def L_sub_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    return _check_i64(_int(a, span) - _int(b, span), span, "integer subtraction overflows")


def L_mul_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    return _check_i64(_int(a, span) * _int(b, span), span, "integer multiplication overflows")


def L_div_trunc_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    lhs = _int(a, span)
    rhs = _int(b, span)
    if rhs == 0:
        L_fault("L4002", "integer division by zero", span)
    if lhs == INT_MIN and rhs == -1:
        L_fault("L4004", "integer division overflows", span)
    q = abs(lhs) // abs(rhs)
    if (lhs < 0) != (rhs < 0):
        q = -q
    return _check_i64(q, span, "integer division overflows")


def L_rem_trunc_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    lhs = _int(a, span)
    rhs = _int(b, span)
    if rhs == 0:
        L_fault("L4002", "integer remainder by zero", span)
    if lhs == INT_MIN and rhs == -1:
        L_fault("L4004", "integer remainder overflows", span)
    return _check_i64(
        lhs - L_div_trunc_i64(lhs, rhs, span) * rhs,
        span,
        "integer remainder overflows",
    )


def L_pow_i64(a: object, b: object, span: tuple[int, int, int]) -> int:
    base = _int(a, span)
    exp = _int(b, span)
    if exp < 0:
        L_fault("L4005", "integer exponent must be non-negative; use float operands", span)
    if exp > U32_MAX:
        L_fault("L4004", "integer exponentiation overflows", span)
    result = 1
    factor = base
    n = exp
    while n > 0:
        if n & 1:
            result = _check_i64(result * factor, span, "integer exponentiation overflows")
        n >>= 1
        if n > 0:
            factor = _check_i64(factor * factor, span, "integer exponentiation overflows")
    return result


def _numeric_kind_fault(span: tuple[int, int, int]) -> None:
    L_fault("L5001", "numeric operands must both be `int` or both be `float`", span)


def _float_div(a: float, b: float) -> float:
    if b == 0.0:
        if a == 0.0 or math.isnan(a) or math.isnan(b):
            return math.nan
        sign = math.copysign(1.0, a) * math.copysign(1.0, b)
        return math.copysign(math.inf, sign)
    return a / b


def _float_pow(a: float, b: float) -> float:
    if a == 0.0 and b < 0.0:
        negative_sign = math.copysign(1.0, a) < 0.0 and b.is_integer() and int(abs(b)) % 2 == 1
        return math.copysign(math.inf, -1.0 if negative_sign else 1.0)
    if math.isfinite(a) and a < 0.0 and math.isfinite(b) and not b.is_integer():
        return math.nan
    try:
        result = a**b
    except ValueError:
        return math.nan
    except ZeroDivisionError:
        if a == 0.0 and b < 0.0:
            negative_sign = math.copysign(1.0, a) < 0.0 and b.is_integer() and int(abs(b)) % 2 == 1
            return math.copysign(math.inf, -1.0 if negative_sign else 1.0)
        return math.nan
    except OverflowError:
        sign = -1.0 if a < 0.0 and b.is_integer() and int(abs(b)) % 2 == 1 else 1.0
        return math.copysign(math.inf, sign)
    if type(result) is complex:
        return math.nan
    return result


def L_add(a: object, b: object, span: tuple[int, int, int]) -> int | float | str:
    if type(a) is int and type(b) is int:
        return L_add_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a + b
    if type(a) is str and type(b) is str:
        return a + b
    _numeric_kind_fault(span)


def L_sub(a: object, b: object, span: tuple[int, int, int]) -> int | float:
    if type(a) is int and type(b) is int:
        return L_sub_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a - b
    _numeric_kind_fault(span)


def L_mul(a: object, b: object, span: tuple[int, int, int]) -> int | float:
    if type(a) is int and type(b) is int:
        return L_mul_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a * b
    _numeric_kind_fault(span)


def L_div(a: object, b: object, span: tuple[int, int, int]) -> int | float:
    if type(a) is int and type(b) is int:
        return L_div_trunc_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return _float_div(a, b)
    _numeric_kind_fault(span)


def L_pow(a: object, b: object, span: tuple[int, int, int]) -> int | float:
    if type(a) is int and type(b) is int:
        return L_pow_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return _float_pow(a, b)
    _numeric_kind_fault(span)


def L_neg(value: object, span: tuple[int, int, int]) -> int | float:
    if type(value) is int:
        return L_sub_i64(0, value, span)
    if type(value) is float:
        return -value
    L_fault("L5001", "numeric operand must be `int` or `float`", span)


def _non_comparable_kind(value: object) -> str | None:
    if isinstance(value, LMap):
        return "Map"
    if isinstance(value, LSet):
        return "Set"
    if isinstance(value, LFile):
        return "File"
    if isinstance(value, LJson):
        return "JSONValue"
    if isinstance(value, LRange):
        return "range"
    if isinstance(value, (LComposed, LHostCallable, LExternFunction)) or callable(value):
        return "function"
    return None


def _cmp_guard_not_comparable(kind: str, span: tuple[int, int, int]) -> None:
    L_fault("L5007", "`" + kind + "` values are not comparable", span)


def _L_values_equal(
    a: object,
    b: object,
    span: tuple[int, int, int],
    budget: _StructBudget | None = None,
    depth: int = 0,
) -> bool:
    if budget is None:
        budget = _StructBudget()
    budget.consume(depth, span)
    kind = _non_comparable_kind(a) or _non_comparable_kind(b)
    if kind is not None:
        _cmp_guard_not_comparable(kind, span)

    if type(a) is bool and type(b) is bool:
        return a == b
    if type(a) is int and type(b) is int:
        return a == b
    if type(a) is float and type(b) is float:
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return a.data == b.data
    if a is L_UNIT and b is L_UNIT:
        return True
    if a is L_NULL and b is L_NULL:
        return True
    if a is None and b is None:
        return True
    if isinstance(a, Some) and isinstance(b, Some):
        return _L_values_equal(a.value, b.value, span, budget, depth + 1)
    if isinstance(a, Ok) and isinstance(b, Ok):
        return _L_values_equal(a.value, b.value, span, budget, depth + 1)
    if isinstance(a, Err) and isinstance(b, Err):
        return _L_values_equal(a.value, b.value, span, budget, depth + 1)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        for left, right in zip(a, b):
            if not _L_values_equal(left, right, span, budget, depth + 1):
                return False
        return True
    if _is_langl_newtype(a) and _is_langl_newtype(b):
        if a.newtype_id != b.newtype_id:
            return False
        return _L_values_equal(a.value, b.value, span, budget, depth + 1)
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        return False
    if _is_langl_enum(a) and _is_langl_enum(b):
        if a.enum_id != b.enum_id or a.variant != b.variant:
            return False
        if len(a.payloads) != len(b.payloads):
            return False
        for left, right in zip(a.payloads, b.payloads):
            if not _L_values_equal(left, right, span, budget, depth + 1):
                return False
        return True
    if _is_langl_enum(a) or _is_langl_enum(b):
        return False
    if _is_langl_nominal_record(a) and _is_langl_nominal_record(b):
        if a.__langl_record_id__ != b.__langl_record_id__:
            return False
        if len(a.__langl_record_fields__) != len(b.__langl_record_fields__):
            return False
        for (left_field, _), (right_field, _) in zip(a.__langl_record_fields__, b.__langl_record_fields__):
            if not _L_values_equal(
                getattr(a, left_field),
                getattr(b, right_field),
                span,
                budget,
                depth + 1,
            ):
                return False
        return True
    if _is_langl_record(a) and _is_langl_record(b):
        left_fields = sorted(a.__langl_record_fields__, key=lambda item: item[1])
        right_fields = sorted(b.__langl_record_fields__, key=lambda item: item[1])
        if [source for _, source in left_fields] != [source for _, source in right_fields]:
            L_fault("L5007", "records with different field sets are not comparable", span)
        for (left_field, _), (right_field, _) in zip(left_fields, right_fields):
            if not _L_values_equal(
                getattr(a, left_field),
                getattr(b, right_field),
                span,
                budget,
                depth + 1,
            ):
                return False
        return True
    return False


def L_eq(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return _L_values_equal(a, b, span)


def L_ne(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return not _L_values_equal(a, b, span)


def _newtype_order_operands(a: object, b: object, span: tuple[int, int, int]) -> tuple[object, object]:
    if _is_langl_newtype(a) and _is_langl_newtype(b) and a.newtype_id == b.newtype_id:
        return a.value, b.value
    L_fault("L5007", "`newtype` values are not comparable", span)


def _L_order_compare(
    a: object,
    b: object,
    span: tuple[int, int, int],
    budget: _StructBudget | None = None,
    depth: int = 0,
) -> int:
    if budget is None:
        budget = _StructBudget()
    budget.consume(depth, span)
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        left, right = _newtype_order_operands(a, b, span)
        return _L_order_compare(left, right, span, budget, depth + 1)
    if _is_langl_enum(a) or _is_langl_enum(b):
        if not (_is_langl_enum(a) and _is_langl_enum(b)):
            _cmp_guard_not_comparable("enum", span)
        if a.enum_id == "RoundingMode" or b.enum_id == "RoundingMode":
            _cmp_guard_not_comparable("RoundingMode", span)
        if a.enum_id != b.enum_id:
            _cmp_guard_not_comparable("enum", span)
        if a.variant_index != b.variant_index:
            return -1 if a.variant_index < b.variant_index else 1
        for left, right in zip(a.payloads, b.payloads):
            cmp = _L_order_compare(left, right, span, budget, depth + 1)
            if cmp != 0:
                return cmp
        if len(a.payloads) == len(b.payloads):
            return 0
        return -1 if len(a.payloads) < len(b.payloads) else 1
    if type(a) is int and type(b) is int:
        return -1 if a < b else (1 if a > b else 0)
    if type(a) is float and type(b) is float:
        return -1 if a < b else (1 if a > b else 0)
    if type(a) is str and type(b) is str:
        return -1 if a < b else (1 if a > b else 0)
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return -1 if a.data < b.data else (1 if a.data > b.data else 0)
    _numeric_kind_fault(span)


def L_lt(a: object, b: object, span: tuple[int, int, int]) -> bool:
    if _is_langl_enum(a) or _is_langl_enum(b):
        return _L_order_compare(a, b, span) < 0
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        left, right = _newtype_order_operands(a, b, span)
        return L_lt(left, right, span)
    if type(a) is int and type(b) is int:
        return L_lt_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a < b
    if type(a) is str and type(b) is str:
        return a < b
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return a.data < b.data
    _numeric_kind_fault(span)


def L_le(a: object, b: object, span: tuple[int, int, int]) -> bool:
    if _is_langl_enum(a) or _is_langl_enum(b):
        return _L_order_compare(a, b, span) <= 0
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        left, right = _newtype_order_operands(a, b, span)
        return L_le(left, right, span)
    if type(a) is int and type(b) is int:
        return L_le_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a <= b
    if type(a) is str and type(b) is str:
        return a <= b
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return a.data <= b.data
    _numeric_kind_fault(span)


def L_gt(a: object, b: object, span: tuple[int, int, int]) -> bool:
    if _is_langl_enum(a) or _is_langl_enum(b):
        return _L_order_compare(a, b, span) > 0
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        left, right = _newtype_order_operands(a, b, span)
        return L_gt(left, right, span)
    if type(a) is int and type(b) is int:
        return L_gt_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a > b
    if type(a) is str and type(b) is str:
        return a > b
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return a.data > b.data
    _numeric_kind_fault(span)


def L_ge(a: object, b: object, span: tuple[int, int, int]) -> bool:
    if _is_langl_enum(a) or _is_langl_enum(b):
        return _L_order_compare(a, b, span) >= 0
    if _is_langl_newtype(a) or _is_langl_newtype(b):
        left, right = _newtype_order_operands(a, b, span)
        return L_ge(left, right, span)
    if type(a) is int and type(b) is int:
        return L_ge_i64(a, b, span)
    if type(a) is float and type(b) is float:
        return a >= b
    if type(a) is str and type(b) is str:
        return a >= b
    if isinstance(a, LBytes) and isinstance(b, LBytes):
        return a.data >= b.data
    _numeric_kind_fault(span)


def L_lt_i64(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return _int(a, span) < _int(b, span)


def L_le_i64(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return _int(a, span) <= _int(b, span)


def L_gt_i64(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return _int(a, span) > _int(b, span)


def L_ge_i64(a: object, b: object, span: tuple[int, int, int]) -> bool:
    return _int(a, span) >= _int(b, span)


def L_condition(value: object, span: tuple[int, int, int]) -> bool:
    if type(value) is not bool:
        L_fault("L5001", "condition must be `bool`", span)
    return value


def L_coalesce(value: object, rhs) -> object:
    if isinstance(value, Some):
        return value.value
    if value is None or value is L_NULL:
        return rhs()
    return value


def L_to_int(value: object, span: tuple[int, int, int]) -> Some | None:
    if not isinstance(value, str):
        L_fault("L5001", "`toInt` takes a `string`", span)
    try:
        parsed = int(value.strip(), 10)
    except ValueError:
        return None
    if parsed < INT_MIN or parsed > INT_MAX:
        return None
    return Some(parsed)


def _string_arg(value: object, label: str, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", label + " takes a `string`, found `" + L_kind(value) + "`", span)
    return value


def L_string_starts_with(value: object, prefix: object, span: tuple[int, int, int]) -> bool:
    if not isinstance(value, str):
        L_fault("L5001", "`str.startsWith` takes a string receiver", span)
    return value.startswith(_string_arg(prefix, "`str.startsWith`", span))


def L_string_ends_with(value: object, suffix: object, span: tuple[int, int, int]) -> bool:
    if not isinstance(value, str):
        L_fault("L5001", "`str.endsWith` takes a string receiver", span)
    return value.endswith(_string_arg(suffix, "`str.endsWith`", span))


def L_string_contains(value: object, sub: object, span: tuple[int, int, int]) -> bool:
    if not isinstance(value, str):
        L_fault("L5001", "`str.contains` takes a string receiver", span)
    return _string_arg(sub, "`str.contains`", span) in value


def L_string_index_of(value: object, sub: object, span: tuple[int, int, int]) -> Some | None:
    if not isinstance(value, str):
        L_fault("L5001", "`str.indexOf` takes a string receiver", span)
    idx = value.find(_string_arg(sub, "`str.indexOf`", span))
    return Some(idx) if idx >= 0 else None


def L_string_last_index_of(value: object, sub: object, span: tuple[int, int, int]) -> Some | None:
    if not isinstance(value, str):
        L_fault("L5001", "`str.lastIndexOf` takes a string receiver", span)
    idx = value.rfind(_string_arg(sub, "`str.lastIndexOf`", span))
    return Some(idx) if idx >= 0 else None


def L_string_trim(value: object, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", "`str.trim` takes a string receiver", span)
    return value.strip(" \t\n\r")


def L_string_trim_start(value: object, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", "`str.trimStart` takes a string receiver", span)
    return value.lstrip(" \t\n\r")


def L_string_trim_end(value: object, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", "`str.trimEnd` takes a string receiver", span)
    return value.rstrip(" \t\n\r")


def L_string_split(value: object, sep: object, span: tuple[int, int, int]) -> list[str]:
    if not isinstance(value, str) or not isinstance(sep, str):
        L_fault("L5001", "`split` takes strings", span)
    if sep == "":
        L_fault(
            "L5001",
            "`str.split` needs a non-empty separator; use `.scalars()` for a scalar split",
            span,
        )
    return value.split(sep)


def L_string_code_point_at(value: object, index: object, span: tuple[int, int, int]) -> Some | None:
    if not isinstance(value, str):
        L_fault("L5001", "`codePointAt` takes a string", span)
    idx = _int(index, span)
    if idx < 0 or idx >= len(value):
        return None
    return Some(ord(value[idx]))


def L_string_byte_length(value: object, span: tuple[int, int, int]) -> int:
    if not isinstance(value, str):
        L_fault("L5001", "`byteLength` takes a string", span)
    return len(value.encode("utf-8"))


def L_string_slice(value: object, start: object, end: object, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", "`str.slice` takes a string receiver", span)
    st = _int(start, span)
    en = _int(end, span)
    length = len(value)
    st = max(0, min(st, length))
    en = max(st, min(en, length))
    return value[st:en]


def L_string_replace(value: object, needle: object, replacement: object, span: tuple[int, int, int]) -> str:
    if not isinstance(value, str):
        L_fault("L5001", "`str.replace` takes a string receiver", span)
    return value.replace(
        _string_arg(needle, "`str.replace` needle", span),
        _string_arg(replacement, "`str.replace` replacement", span),
    )


def L_array_get(value: object, index: object, span: tuple[int, int, int]) -> Some | None:
    idx = _int(index, span)
    if not isinstance(value, list):
        L_fault("L5001", "`arr.get` takes an array receiver", span)
    if idx < 0 or idx >= len(value):
        return None
    return Some(value[idx])


def _array_receiver(value: object, method: str, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "`arr." + method + "` takes an array receiver", span)
    return value


def L_array_push(value: object, item: object, span: tuple[int, int, int]) -> object:
    _array_receiver(value, "push", span).append(item)
    return L_UNIT


def L_array_slice(value: object, start: object, end: object, span: tuple[int, int, int]) -> list[object]:
    items = _array_receiver(value, "slice", span)
    if type(start) is not int:
        L_fault("L5001", "`arr.slice` takes `int` bounds, found `" + L_kind(start) + "`", span)
    if type(end) is not int:
        L_fault("L5001", "`arr.slice` takes `int` bounds, found `" + L_kind(end) + "`", span)
    length = len(items)
    st = max(0, min(start, length))
    en = max(st, min(end, length))
    return list(items[st:en])


def L_array_join(value: object, sep: object, span: tuple[int, int, int]) -> str:
    items = _array_receiver(value, "join", span)
    if not isinstance(sep, str):
        L_fault("L5001", "`arr.join` takes a `string`, found `" + L_kind(sep) + "`", span)
    return sep.join(L_render(item) for item in items)


def L_array_index_of(value: object, needle: object, span: tuple[int, int, int]) -> Some | None:
    items = _array_receiver(value, "indexOf", span)
    for idx, item in enumerate(items):
        if _L_values_equal(item, needle, span):
            return Some(idx)
    return None


def L_array_pop(value: object, span: tuple[int, int, int]) -> Some | None:
    items = _array_receiver(value, "pop", span)
    if not items:
        return None
    return Some(items.pop())


def L_array_clear(value: object, span: tuple[int, int, int]) -> object:
    _array_receiver(value, "clear", span).clear()
    return L_UNIT


def L_array_reverse(value: object, span: tuple[int, int, int]) -> object:
    _array_receiver(value, "reverse", span).reverse()
    return L_UNIT


def L_array_insert(value: object, index: object, item: object, span: tuple[int, int, int]) -> object:
    items = _array_receiver(value, "insert", span)
    if type(index) is not int:
        L_fault("L5001", "`arr.insert` takes an `int` index, found `" + L_kind(index) + "`", span)
    length = len(items)
    if index < 0 or index > length:
        L_fault("L4001", "index " + str(index) + " out of bounds for insert into length " + str(length) + " (§6.5)", span)
    items.insert(index, item)
    return L_UNIT


def L_array_remove_at(value: object, index: object, span: tuple[int, int, int]) -> Some | None:
    items = _array_receiver(value, "removeAt", span)
    if type(index) is not int:
        L_fault("L5001", "`arr.removeAt` takes an `int` index, found `" + L_kind(index) + "`", span)
    if index < 0 or index >= len(items):
        return None
    return Some(items.pop(index))


def L_array_map(value: object, callback: object, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "`map` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`map` callback must be callable", span)
    return [callback(item) for item in list(value)]


def L_array_map__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`map` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`map` callback must be callable", span)
    out: list[object] = []
    for item in list(value):
        out.append((yield from _L_call_callback_co(callback, (item,), span)))
    return out


def L_array_filter(value: object, callback: object, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "`filter` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`filter` callback must be callable", span)
    out: list[object] = []
    for item in list(value):
        if L_condition(callback(item), span):
            out.append(item)
    return out


def L_array_filter__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`filter` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`filter` callback must be callable", span)
    out: list[object] = []
    for item in list(value):
        if L_condition((yield from _L_call_callback_co(callback, (item,), span)), span):
            out.append(item)
    return out


def L_array_reduce(value: object, initial: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`reduce` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`reduce` callback must be callable", span)
    acc = initial
    for item in list(value):
        acc = callback(acc, item)
    return acc


def L_array_reduce__co(value: object, initial: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`reduce` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`reduce` callback must be callable", span)
    acc = initial
    for item in list(value):
        acc = yield from _L_call_callback_co(callback, (acc, item), span)
    return acc


def _order_key(value: object, method: str, span: tuple[int, int, int]) -> tuple[int, object]:
    if type(value) is int:
        return (0, value)
    if type(value) is float:
        return (1, value)
    if isinstance(value, str):
        return (2, value)
    if isinstance(value, LBytes):
        return (3, value.data)
    if _is_langl_enum(value):
        if value.enum_id == "RoundingMode":
            _cmp_guard_not_comparable("RoundingMode", span)
        return (
            4,
            value.enum_id,
            value.variant_index,
            tuple(_order_key(item, method, span) for item in value.payloads),
        )
    L_fault("L5001", "`" + method + "` key is not order-comparable: `" + L_kind(value) + "`", span)


def L_array_sorted(value: object, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "`sorted` takes an array receiver", span)
    keyed = [(_order_key(item, "sorted", span), idx, item) for idx, item in enumerate(list(value))]
    return [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]


def L_array_sort(value: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`sort` takes an array receiver", span)
    keyed = [(_order_key(item, "sort", span), idx, item) for idx, item in enumerate(list(value))]
    value[:] = [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]
    return L_UNIT


def L_array_sorted_by(value: object, callback: object, span: tuple[int, int, int]) -> list[object]:
    if not isinstance(value, list):
        L_fault("L5001", "`sortedBy` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`sortedBy` callback must be callable", span)
    items = list(value)
    keys = [callback(item) for item in items]
    keyed = [(_order_key(key, "sortedBy", span), idx, item) for idx, (key, item) in enumerate(zip(keys, items))]
    return [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]


def L_array_sorted_by__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`sortedBy` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`sortedBy` callback must be callable", span)
    items = list(value)
    keys: list[object] = []
    for item in items:
        keys.append((yield from _L_call_callback_co(callback, (item,), span)))
    keyed = [(_order_key(key, "sortedBy", span), idx, item) for idx, (key, item) in enumerate(zip(keys, items))]
    return [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]


def L_array_sort_by(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`sortBy` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`sortBy` callback must be callable", span)
    items = list(value)
    keys = [callback(item) for item in items]
    keyed = [(_order_key(key, "sortBy", span), idx, item) for idx, (key, item) in enumerate(zip(keys, items))]
    value[:] = [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]
    return L_UNIT


def L_array_sort_by__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`sortBy` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`sortBy` callback must be callable", span)
    items = list(value)
    keys: list[object] = []
    for item in items:
        keys.append((yield from _L_call_callback_co(callback, (item,), span)))
    keyed = [(_order_key(key, "sortBy", span), idx, item) for idx, (key, item) in enumerate(zip(keys, items))]
    value[:] = [item for _key, _idx, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]
    return L_UNIT


def L_array_retain(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`retain` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`retain` callback must be callable", span)
    kept: list[object] = []
    for item in list(value):
        if L_condition(callback(item), span):
            kept.append(item)
    value[:] = kept
    return L_UNIT


def L_array_retain__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if not isinstance(value, list):
        L_fault("L5001", "`retain` takes an array receiver", span)
    if not callable(callback):
        L_fault("L5001", "`retain` callback must be callable", span)
    kept: list[object] = []
    for item in list(value):
        if L_condition((yield from _L_call_callback_co(callback, (item,), span)), span):
            kept.append(item)
    value[:] = kept
    return L_UNIT


def L_option_map(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if value is None:
        return None
    if not isinstance(value, Some):
        L_fault("L5001", "`Option.map` takes an Option receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Option.map` callback must be callable", span)
    return Some(callback(value.value))


def L_option_map__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if value is None:
        return None
    if not isinstance(value, Some):
        L_fault("L5001", "`Option.map` takes an Option receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Option.map` callback must be callable", span)
    return Some((yield from _L_call_callback_co(callback, (value.value,), span)))


def L_option_flat_map(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if value is None:
        return None
    if not isinstance(value, Some):
        L_fault("L5001", "`Option.flatMap` takes an Option receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Option.flatMap` callback must be callable", span)
    out = callback(value.value)
    if out is None or isinstance(out, Some):
        return out
    L_fault("L5001", "`Option.flatMap` callback must return Option", span)


def L_option_flat_map__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if value is None:
        return None
    if not isinstance(value, Some):
        L_fault("L5001", "`Option.flatMap` takes an Option receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Option.flatMap` callback must be callable", span)
    out = yield from _L_call_callback_co(callback, (value.value,), span)
    if out is None or isinstance(out, Some):
        return out
    L_fault("L5001", "`Option.flatMap` callback must return Option", span)


def L_option_ok_or_else(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Some):
        return Ok(value.value)
    if value is None:
        if not callable(callback):
            L_fault("L5001", "`Option.okOrElse` callback must be callable", span)
        return Err(callback())
    L_no_member(value, "okOrElse", span)


def L_option_ok_or_else__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Some):
        return Ok(value.value)
    if value is None:
        if not callable(callback):
            L_fault("L5001", "`Option.okOrElse` callback must be callable", span)
        return Err((yield from _L_call_callback_co(callback, (), span)))
    L_no_member(value, "okOrElse", span)


def L_option_ok_or(value: object, error: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Some):
        return Ok(value.value)
    if value is None:
        return Err(error)
    L_no_member(value, "okOr", span)


def L_result_map(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Err):
        return value
    if not isinstance(value, Ok):
        L_fault("L5001", "`Result.map` takes a Result receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Result.map` callback must be callable", span)
    return Ok(callback(value.value))


def L_result_map__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Err):
        return value
    if not isinstance(value, Ok):
        L_fault("L5001", "`Result.map` takes a Result receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Result.map` callback must be callable", span)
    return Ok((yield from _L_call_callback_co(callback, (value.value,), span)))


def L_result_flat_map(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Err):
        return value
    if not isinstance(value, Ok):
        L_fault("L5001", "`Result.flatMap` takes a Result receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Result.flatMap` callback must be callable", span)
    out = callback(value.value)
    if isinstance(out, Ok) or isinstance(out, Err):
        return out
    L_fault("L5001", "`Result.flatMap` callback must return Result", span)


def L_result_flat_map__co(value: object, callback: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, Err):
        return value
    if not isinstance(value, Ok):
        L_fault("L5001", "`Result.flatMap` takes a Result receiver", span)
    if not callable(callback):
        L_fault("L5001", "`Result.flatMap` callback must be callable", span)
    out = yield from _L_call_callback_co(callback, (value.value,), span)
    if isinstance(out, Ok) or isinstance(out, Err):
        return out
    L_fault("L5001", "`Result.flatMap` callback must return Result", span)


def L_index(value: object, index: object, span: tuple[int, int, int]) -> object:
    if isinstance(value, str):
        L_fault("L5001", "strings are not indexable; use `s.scalars()` (§1)", span)
    if isinstance(value, list):
        if type(index) is not int:
            L_fault("L5001", "cannot index `Array` with `" + L_kind(index) + "`", span)
        if index < 0 or index >= len(value):
            L_fault(
                "L4001",
                "index " + str(index) + " is out of bounds for an array of length " + str(len(value)),
                span,
            )
        return value[index]
    L_fault(
        "L5001",
        "cannot index `" + L_kind(value) + "` with `" + L_kind(index) + "`",
        span,
    )


def L_index_slot(value: object, index: object, span: tuple[int, int, int]) -> tuple[list, int]:
    if not isinstance(value, list):
        L_fault(
            "L5001",
            "cannot index-assign `" + L_kind(value) + "`; only Array cells are index-assignable (§9)",
            span,
        )
    if type(index) is not int:
        L_fault("L5001", "array indices are `int`, found `" + L_kind(index) + "`", span)
    if index < 0 or index >= len(value):
        L_fault("L4001", "index " + str(index) + " out of bounds for length " + str(len(value)) + " (§13a)", span)
    return (value, index)


def L_index_slot_set(slot: tuple[list, int], value: object) -> None:
    items, index = slot
    items[index] = value


def L_index_slot_get(slot: tuple[list, int]) -> object:
    items, index = slot
    return items[index]


def L_index_slot_is_empty(slot: tuple[list, int]) -> bool:
    items, index = slot
    return items[index] is None or items[index] is L_NULL


def L_immutable_assignment(name: object, span: tuple[int, int, int]) -> None:
    if not isinstance(name, str):
        L_fault("L5001", "immutable assignment metadata is malformed", span)
    L_fault("L5003", "`" + name + "` is not `let mut` and cannot be assigned", span)


def L_render(value: object) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is float:
        return L_format_f64(value)
    if value is L_UNIT:
        return "()"
    if value is L_NULL:
        return "null"
    if value is None:
        return "None"
    if isinstance(value, Some):
        return "Some(" + L_render(value.value) + ")"
    if isinstance(value, Ok):
        return "Ok(" + L_render(value.value) + ")"
    if isinstance(value, Err):
        return "Err(" + L_render(value.value) + ")"
    if isinstance(value, LBytes):
        return "Bytes(" + L_bytes_to_hex(value) + ")"
    if isinstance(value, LMap):
        parts = []
        for key, item in value.entries:
            parts.append(L_render(_key_to_value(key)) + ": " + L_render(item))
        return "Map{" + ", ".join(parts) + "}"
    if isinstance(value, LSet):
        return "Set{" + ", ".join(L_render(_key_to_value(key)) for key in value.items) + "}"
    if isinstance(value, LRange):
        out = str(value.lo) + (".." if value.inclusive else "..<") + str(value.hi)
        if value.step != 1:
            out += " by " + str(value.step)
        return out
    if isinstance(value, list):
        return "[" + ", ".join(L_render(item) for item in value) + "]"
    if _is_langl_newtype(value):
        return value.newtype_id + "(" + L_render(value.value) + ")"
    if _is_langl_enum(value):
        if len(value.payloads) == 0:
            return value.enum_id + "." + value.variant
        return value.enum_id + "." + value.variant + "(" + ", ".join(L_render(item) for item in value.payloads) + ")"
    if _is_langl_nominal_record(value):
        fields = [
            source_field + ": " + L_render(getattr(value, py_field))
            for py_field, source_field in value.__langl_record_fields__
        ]
        if not fields:
            return value.__langl_record_id__ + " {}"
        return value.__langl_record_id__ + " { " + ", ".join(fields) + " }"
    if _is_langl_record(value):
        fields = [
            source_field + ": " + L_render(getattr(value, py_field))
            for py_field, source_field in sorted(
                value.__langl_record_fields__, key=lambda item: item[1]
            )
        ]
        return "{ " + ", ".join(fields) + " }"
    return str(value)
