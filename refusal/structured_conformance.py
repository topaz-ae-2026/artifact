"""Field-level conformance check for the 17 recognized Study A refusals.

The script prefers expected-case metadata already emitted by
build_refusal_suite.py. If no manifest is present, it discovers the existing
recognized .l inputs and derives expectations from the registered token and
its source context.

Usage:
    GATE_BIN=... python refusal/structured_conformance.py
    python refusal/structured_conformance.py --suite-dir refusal/cases
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = Path(__file__).resolve().parent
langl_DEFAULT = _require_env("GATE_BIN")

REGISTRY = {
    "eval": ("L5201", "dynamic-evaluation"),
    "exec": ("L5201", "dynamic-evaluation"),
    "compile": ("L5201", "dynamic-evaluation"),
    "Function": ("L5201", "dynamic-evaluation"),
    "ffi": ("L5202", "host-interop-ffi"),
    "native": ("L5202", "host-interop-ffi"),
    "extern": ("L5202", "host-interop-ffi"),
    "syscall": ("L5202", "host-interop-ffi"),
    "macro": ("L5203", "macro-source-generation"),
    "defmacro": ("L5203", "macro-source-generation"),
    "quote": ("L5203", "macro-source-generation"),
    "unquote": ("L5203", "macro-source-generation"),
    "reflect": ("L5204", "runtime-reflection"),
    "getattr": ("L5204", "runtime-reflection"),
    "setattr": ("L5204", "runtime-reflection"),
    "globals": ("L5204", "runtime-reflection"),
    "locals": ("L5204", "runtime-reflection"),
    "introspect": ("L5204", "runtime-reflection"),
    "require": ("L5205", "dynamic-module-loading"),
    "dlopen": ("L5205", "dynamic-module-loading"),
    "import_module": ("L5205", "dynamic-module-loading"),
    "__import__": ("L5205", "dynamic-module-loading"),
    "loadModule": ("L5205", "dynamic-module-loading"),
}

FORMS = {
    "value": "value-reference",
    "value-use": "value-reference",
    "value-reference": "value-reference",
    "callee": "direct-call",
    "call": "direct-call",
    "direct-call": "direct-call",
    "member": "member-access",
    "member-access": "member-access",
    "forward": "forward-reference",
    "forward-reference": "forward-reference",
}


@dataclass(frozen=True)
class Case:
    case_id: str
    path: Path
    token: str
    code: str
    family: str
    request_form: str


def read_source(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if stdout and stderr and not stdout.endswith(("\n", "\r")):
        return stdout + "\n" + stderr
    return stdout + stderr


def check(langl: str, path: Path, json_format: bool) -> tuple[int, str]:
    command = [langl, "check"]
    if json_format:
        command.extend(["--format", "json"])
    command.append(str(path))
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, combined_output(proc)


def json_objects(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
        elif isinstance(value, list):
            objects.extend(item for item in value if isinstance(item, dict))
    if objects:
        return objects

    decoder = json.JSONDecoder()
    offset = 0
    while offset < len(text):
        start = text.find("{", offset)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            offset = start + 1
            continue
        if isinstance(value, dict):
            objects.append(value)
        offset = end
    return objects


def mask_non_code(source: str) -> str:
    chars = list(source)
    i = 0
    state = "code"
    while i < len(chars):
        c = chars[i]
        n = chars[i + 1] if i + 1 < len(chars) else ""
        if state == "code":
            if c == '"':
                chars[i] = " "
                state = "string"
            elif c == "/" and n == "/":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "line-comment"
            elif c == "/" and n == "*":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "block-comment"
        elif state == "string":
            if c == "\\":
                chars[i] = " "
                if i + 1 < len(chars):
                    chars[i + 1] = " "
                    i += 1
            elif c == '"':
                chars[i] = " "
                state = "code"
            elif c == "{":
                # a template interpolation is code, not string text
                chars[i] = " "
                state = "template"
            elif c not in "\r\n":
                chars[i] = " "
        elif state == "template":
            if c == "}":
                chars[i] = " "
                state = "string"
        elif state == "line-comment":
            if c in "\r\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block-comment":
            if c == "*" and n == "/":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "code"
            elif c not in "\r\n":
                chars[i] = " "
        i += 1
    return "".join(chars)


def token_occurrences(source: str, token: str) -> list[int]:
    masked = mask_non_code(source)
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])"
    )
    return [match.start() for match in pattern.finditer(masked)]


def registered_tokens(source: str) -> list[str]:
    found = []
    for token in REGISTRY:
        if token_occurrences(source, token):
            found.append(token)
    return found


def normalize_form(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return FORMS.get(value.strip().lower())


def infer_form(path: Path, source: str, token: str) -> str:
    label = str(path).lower()
    for marker, form in (
        ("forward", "forward-reference"),
        ("member", "member-access"),
        ("callee", "direct-call"),
        ("direct-call", "direct-call"),
        ("value", "value-reference"),
    ):
        if marker in label:
            return form

    masked = mask_non_code(source)
    forms = set()
    for offset in token_occurrences(source, token):
        left = offset - 1
        while left >= 0 and masked[left].isspace():
            left -= 1
        right = offset + len(token)
        while right < len(masked) and masked[right].isspace():
            right += 1
        if left >= 0 and masked[left] == ".":
            forms.add("member-access")
        elif right < len(masked) and masked[right] == "(":
            forms.add("direct-call")
        else:
            forms.add("value-reference")

    if len(forms) != 1:
        raise RuntimeError(
            f"cannot infer one request form for {path}: {sorted(forms)}"
        )
    return forms.pop()


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def metadata_cases(root: Path) -> list[Case]:
    cases: dict[Path, Case] = {}
    for manifest in sorted(root.rglob("*.json")):
        if manifest.name.startswith("structured-conformance"):
            continue
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        for raw in walk_dicts(document):
            expected = raw.get("expected")
            merged = dict(raw)
            if isinstance(expected, dict):
                merged.update(expected)

            code = merged.get("expected_code") or merged.get("code")
            recognized = merged.get("recognized")
            if not (
                isinstance(code, str)
                and re.fullmatch(r"L520[1-5]", code)
                or recognized is True
            ):
                continue

            raw_path = (
                merged.get("path")
                or merged.get("file")
                or merged.get("input_path")
                or merged.get("source_path")
            )
            if not isinstance(raw_path, str):
                continue
            path = Path(raw_path)
            if not path.is_absolute():
                local = (manifest.parent / path).resolve()
                path = local if local.exists() else (root / path).resolve()
            if not path.is_file() or path.suffix.lower() != ".l":
                continue

            source = read_source(path)
            token = merged.get("token") or merged.get("name")
            if not isinstance(token, str) or token not in REGISTRY:
                candidates = registered_tokens(source)
                if isinstance(code, str):
                    candidates = [
                        item for item in candidates if REGISTRY[item][0] == code
                    ]
                if len(candidates) != 1:
                    continue
                token = candidates[0]

            expected_code, family = REGISTRY[token]
            request_form = (
                normalize_form(merged.get("requestForm"))
                or normalize_form(merged.get("request_form"))
                or normalize_form(merged.get("site"))
                or infer_form(path, source, token)
            )
            cases[path] = Case(
                case_id=str(merged.get("id") or merged.get("case_id") or path.stem),
                path=path,
                token=token,
                code=expected_code,
                family=family,
                request_form=request_form,
            )
    return sorted(cases.values(), key=lambda item: item.case_id)


def source_cases(langl: str, root: Path) -> list[Case]:
    paths = sorted(root.rglob("*.l"))
    marked = [
        path
        for path in paths
        if "recognized" in {part.lower() for part in path.parts}
        or "recognized" in path.stem.lower()
    ]
    if len(marked) == 17:
        paths = marked
    else:
        recognized = []
        for path in paths:
            _, output = check(langl, path, json_format=False)
            if re.search(r"L520[1-5]", output):
                recognized.append(path)
        paths = recognized

    cases = []
    for path in paths:
        source = read_source(path)
        candidates = registered_tokens(source)
        if len(candidates) != 1:
            raise RuntimeError(
                f"{path} must contain one distinct registered token, got {candidates}"
            )
        token = candidates[0]
        code, family = REGISTRY[token]
        cases.append(
            Case(
                case_id=path.stem,
                path=path,
                token=token,
                code=code,
                family=family,
                request_form=infer_form(path, source, token),
            )
        )
    return sorted(cases, key=lambda item: item.case_id)


def discover_cases(langl: str, root: Path) -> list[Case]:
    cases = metadata_cases(root)
    if len(cases) != 17:
        cases = source_cases(langl, root)
    if len(cases) != 17:
        raise RuntimeError(
            f"expected 17 recognized Study A inputs, discovered {len(cases)}"
        )
    return cases


def exact_int(value: Any) -> bool:
    return type(value) is int


def schema_ok(record: dict[str, Any]) -> bool:
    if not (
        isinstance(record.get("code"), str)
        and isinstance(record.get("severity"), str)
        and isinstance(record.get("message"), str)
        and isinstance(record.get("secondary"), list)
        and isinstance(record.get("notes"), list)
    ):
        return False

    primary = record.get("primary")
    if not isinstance(primary, dict):
        return False
    if not (
        isinstance(primary.get("file"), str)
        and isinstance(primary.get("message"), str)
        and all(
            exact_int(primary.get(field))
            for field in ("line", "col", "endLine", "endCol", "lo", "hi")
        )
    ):
        return False

    policy = record.get("policy")
    return (
        isinstance(policy, dict)
        and isinstance(policy.get("family"), str)
        and isinstance(policy.get("requestForm"), str)
        and exact_int(policy.get("registryVersion"))
    )


def byte_line_col(source_bytes: bytes, offset: int) -> tuple[int, int]:
    prefix = source_bytes[:offset].decode("utf-8")
    line = prefix.count("\n") + 1
    tail = prefix.rsplit("\n", 1)[-1]
    return line, len(tail) + 1


def span_ok(record: dict[str, Any], source: str, token: str) -> bool:
    primary = record.get("primary")
    if not isinstance(primary, dict):
        return False
    lo = primary.get("lo")
    hi = primary.get("hi")
    if not exact_int(lo) or not exact_int(hi) or lo < 0 or hi < lo:
        return False

    encoded = source.encode("utf-8")
    if hi > len(encoded):
        return False
    try:
        selected = encoded[lo:hi].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if selected != token:
        return False

    line, col = byte_line_col(encoded, lo)
    end_line, end_col = byte_line_col(encoded, hi)
    return (
        primary.get("line") == line
        and primary.get("col") == col
        and primary.get("endLine") == end_line
        and primary.get("endCol") == end_col
    )


def evaluate_case(langl: str, case: Case) -> dict[str, Any]:
    source = read_source(case.path)
    human_rc, human = check(langl, case.path, json_format=False)
    json_rc, rendered = check(langl, case.path, json_format=True)
    records = json_objects(rendered)
    L52 = [
        record
        for record in records
        if re.fullmatch(r"L52\d{2}", str(record.get("code", "")))
    ]
    human_codes = re.findall(r"L52\d{2}", human)
    record = L52[0] if len(L52) == 1 else None
    policy = record.get("policy") if isinstance(record, dict) else None

    checks = {
        "expected_code": bool(record and record.get("code") == case.code),
        "family": bool(
            isinstance(policy, dict) and policy.get("family") == case.family
        ),
        "request_form": bool(
            isinstance(policy, dict)
            and policy.get("requestForm") == case.request_form
        ),
        "registry_version": bool(
            isinstance(policy, dict)
            and type(policy.get("registryVersion")) is int
            and policy.get("registryVersion") == 1
        ),
        "required_fields_and_types": bool(record and schema_ok(record)),
        "registered_token_span": bool(
            record and span_ok(record, source, case.token)
        ),
        "exactly_one_L52": len(L52) == 1,
        "human_json_same_code": bool(
            record
            and len(human_codes) == 1
            and human_codes[0] == record.get("code")
        ),
    }
    return {
        "case": case.case_id,
        "path": str(case.path),
        "expected": {
            "code": case.code,
            "family": case.family,
            "requestForm": case.request_form,
            "token": case.token,
        },
        "returncodes": {"human": human_rc, "json": json_rc},
        "human_codes": human_codes,
        "json_codes": [record.get("code") for record in records],
        "checks": checks,
    }


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--langl", default=langl_DEFAULT)
    parser.add_argument("--suite-dir", type=Path, default=HERE)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "structured-conformance.json",
    )
    args = parser.parse_args()

    cases = discover_cases(args.langl, args.suite_dir.resolve())
    results = [evaluate_case(args.langl, case) for case in cases]
    properties = ["recognized_inputs"] + list(results[0]["checks"])
    table = [{"property": "recognized_inputs", "correct": 17, "total": 17}]
    for prop in properties[1:]:
        table.append(
            {
                "property": prop,
                "correct": sum(result["checks"][prop] for result in results),
                "total": len(results),
            }
        )

    document = {
        "compiler": args.langl,
        "recognized_cases": len(results),
        "summary": table,
        "all_conform": all(row["correct"] == row["total"] for row in table),
        "cases": results,
    }
    atomic_json(args.output, document)

    width = max(len(row["property"]) for row in table)
    print(f"{'property':<{width}}  correct/total")
    for row in table:
        print(
            f"{row['property']:<{width}}  "
            f"{row['correct']}/{row['total']}"
        )
    print(f"json: {args.output}")
    return 0 if document["all_conform"] else 1


if __name__ == "__main__":
    sys.exit(main())
