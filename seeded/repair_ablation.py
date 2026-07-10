"""Study D diagnostic-value repair ablation.

Population:
    24 frozen Study B capability mutants

Conditions:
    C0-none               no diagnostic payload
    C1-generic            captured R0 L5002 diagnostic
    C2-policy-human       live R0+B1 human diagnostic
    C3-policy-structured  live R0+B1 JSON diagnostic

Each cell is a fresh Codex process. Scheduling is repetition-major, with a
deterministically shuffled 24-task x 4-condition block inside each repetition.

Usage:
    python seeded/repair_ablation.py --workers 6
    python seeded/repair_ablation.py --resume --max-cells 192
"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = Path(__file__).resolve().parent
PILOT = (HERE / ".." / "pilot").resolve()
CASES = HERE / "cases"
RUNS = HERE / "repair-runs"
ISO = HERE / "_repair_iso"
langl = _require_env("GATE_BIN")
CODEX = _require_env("CODEX_BIN")
MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "medium"
REPS = 3
SEED = 52026
CALL_TIMEOUT = 420
CHECK_TIMEOUT = 60
RUN_TIMEOUT = 120

CONDITIONS = (
    "C0-none",
    "C1-generic",
    "C2-policy-human",
    "C3-policy-structured",
)

# Source of truth is compiler/crates/langl_check/src/boundary.rs.
# The supplied registry has 23 names, despite the study request saying 25.
REGISTERED_NAMES = (
    "eval",
    "exec",
    "compile",
    "Function",
    "ffi",
    "native",
    "extern",
    "syscall",
    "macro",
    "defmacro",
    "quote",
    "unquote",
    "reflect",
    "getattr",
    "setattr",
    "globals",
    "locals",
    "introspect",
    "require",
    "dlopen",
    "import_module",
    "__import__",
    "loadModule",
)

CODE_BLOCK = re.compile(r"```[A-Za-z0-9_-]*\s*\n(.*?)```", re.DOTALL)
CODE_PATTERN = re.compile(r"L\d{4}")


class AccountLimit(RuntimeError):
    pass


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temporary, path)


def combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if stdout and stderr and not stdout.endswith(("\n", "\r")):
        return stdout + "\n" + stderr
    return stdout + stderr


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
            elif c not in "\r\n":
                chars[i] = " "
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


def registered_bare_names(source: str) -> list[str]:
    """Conservative lexical audit.

    Strings, comments, and qualified members are excluded. A locally defined
    bare homonym remains a hit, so the exact hit list is retained for audit.
    """
    masked = mask_non_code(source)
    hits = set()
    for name in REGISTERED_NAMES:
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"
        )
        for match in pattern.finditer(masked):
            left = match.start() - 1
            while left >= 0 and masked[left].isspace():
                left -= 1
            if left < 0 or masked[left] != ".":
                hits.add(name)
    return sorted(hits)


def expected_lines(task_id: str) -> list[str]:
    path = PILOT / "expected" / f"{task_id}.hidden.txt"
    return read_text(path).splitlines()


def driver(task: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    out = []
    function = task["fn_L"]
    for index, case in enumerate(cases):
        arguments = case["L"]
        if "L_bind" in case:
            out.append(
                case["L_bind"].replace("let e", f"let oracleE{index}")
            )
            arguments = {
                "e": f"oracleE{index}",
                "e, e": f"oracleE{index}, oracleE{index}",
                "e, 0": f"oracleE{index}, 0",
            }[case["L"]]

        returned = task["ret"]
        if returned == "int":
            out.append(f'print("{{{function}({arguments})}}")')
        elif returned == "string":
            out.append(f"print({function}({arguments}))")
        else:
            fields = returned.split(":", 1)[1].split(",")
            out.append(f"let oracleR{index} = {function}({arguments})")
            values = " ".join(
                f"{{oracleR{index}.{field}}}" for field in fields
            )
            out.append(f'print("{values}")')
    return "\n".join(out) + "\n"


def feedback_size(payload: str) -> dict[str, int]:
    return {
        "chars": len(payload),
        "utf8_bytes": len(payload.encode("utf-8")),
        "lines": len(payload.splitlines()),
        "whitespace_tokens": len(re.findall(r"\S+", payload)),
    }


def build_prompt(mutant: str, feedback: str | None) -> str:
    parts = [
        mutant.rstrip(),
        "This program was rejected by the receiving gate of language L.",
    ]
    if feedback is not None:
        parts.append("The gate reported:\n" + feedback)
    parts.append(
        "Produce a corrected complete program that passes the gate and "
        "preserves the intended behavior. Output only the program."
    )
    return "\n\n".join(parts) + "\n"


def walk_values(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def parse_codex_jsonl(stdout: str) -> tuple[str | None, dict[str, int]]:
    messages: list[str] = []
    usage: dict[str, int] = {}
    events = []

    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)

    for event in events:
        if event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    messages.append(text)

        for value in walk_values(event):
            if not isinstance(value, dict):
                continue
            candidate = value.get("usage")
            if not isinstance(candidate, dict):
                continue
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "total_tokens",
            ):
                token_count = candidate.get(key)
                if type(token_count) is int:
                    usage[key] = token_count

    return (messages[-1] if messages else None), usage


def call_frontier(
    prompt: str,
    cell_dir: Path,
) -> tuple[str, dict[str, int], float, int]:
    write_text(cell_dir / "prompt.txt", prompt)
    command = [
        "node",
        CODEX,
        "exec",
        "-c",
        f"model={MODEL}",
        "-c",
        f"model_reasoning_effort={REASONING_EFFORT}",
        "-s",
        "read-only",
        "--skip-git-repo-check",
        "--json",
    ]
    started = time.monotonic()
    proc = subprocess.run(
        command,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CALL_TIMEOUT,
        cwd=ISO,
    )
    duration = time.monotonic() - started
    write_text(cell_dir / "codex.stdout.jsonl", proc.stdout or "")
    write_text(cell_dir / "codex.stderr.txt", proc.stderr or "")

    combined = combined_output(proc)
    lowered = combined.lower()
    if "hit your session limit" in lowered or "usage limit" in lowered:
        raise AccountLimit("account-limit")

    response, usage = parse_codex_jsonl(proc.stdout or "")
    if response is None and proc.returncode == 0:
        response = proc.stdout or ""
    response = response or ""
    write_text(cell_dir / "response.txt", response)
    return response, usage, duration, proc.returncode


def extract_program(response: str) -> str | None:
    blocks = CODE_BLOCK.findall(response)
    if blocks:
        candidate = blocks[-1].strip()
    else:
        candidate = response.strip()
    return candidate + "\n" if candidate else None


def policy_feedback(path: Path) -> dict[str, str]:
    captured = {}
    for condition, json_format in (
        ("C2-policy-human", False),
        ("C3-policy-structured", True),
    ):
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
            timeout=CHECK_TIMEOUT,
        )
        output = combined_output(proc)
        codes = re.findall(r"L52\d{2}", output)
        if proc.returncode == 0 or len(codes) != 1:
            raise RuntimeError(
                f"{path.name}/{condition}: expected one L52xx refusal, "
                f"got rc={proc.returncode}, codes={codes}"
            )
        if json_format:
            records = [
                item
                for item in json_objects(output)
                if re.fullmatch(r"L52\d{2}", str(item.get("code", "")))
            ]
            if len(records) != 1 or not isinstance(
                records[0].get("policy"), dict
            ):
                raise RuntimeError(
                    f"{path.name}: structured feedback lacks one policy record"
                )
        captured[condition] = output
    return captured


def diagnostic_token(
    record: dict[str, Any],
    full_source: str,
) -> str | None:
    primary = record.get("primary")
    if isinstance(primary, dict):
        lo = primary.get("lo")
        hi = primary.get("hi")
        if type(lo) is int and type(hi) is int and 0 <= lo <= hi:
            encoded = full_source.encode("utf-8")
            if hi <= len(encoded):
                try:
                    token = encoded[lo:hi].decode("utf-8")
                except UnicodeDecodeError:
                    token = None
                if token in REGISTERED_NAMES:
                    return token

    message = str(record.get("message", ""))
    for name in REGISTERED_NAMES:
        if f"`{name}`" in message:
            return name
    return None


def terminal_label(code: str | None) -> int:
    if code and code.startswith(("L0", "L1", "L2")):
        return 2
    return 3


def evaluate(
    task: dict[str, Any],
    mutant: str,
    candidate: str,
    cell_dir: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    full_source = candidate + "\n" + driver(task, task["hidden"])
    gated_path = cell_dir / "gated.l"
    write_text(cell_dir / "candidate.l", candidate)
    write_text(gated_path, full_source)

    check_proc = subprocess.run(
        [langl, "check", "--format", "json", str(gated_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CHECK_TIMEOUT,
    )
    check_output = combined_output(check_proc)
    write_text(cell_dir / "check.jsonl", check_output)
    records = [
        item for item in json_objects(check_output) if "code" in item
    ]
    codes = [str(item.get("code")) for item in records]
    if not codes:
        codes = CODE_PATTERN.findall(check_output)
    first_code = codes[0] if codes else None

    L52_records = [
        item
        for item in records
        if re.fullmatch(r"L52\d{2}", str(item.get("code", "")))
    ]
    L52_codes = [
        code for code in codes if re.fullmatch(r"L52\d{2}", code)
    ]
    trigger_names = {
        token
        for token in (
            diagnostic_token(item, full_source) for item in L52_records
        )
        if token is not None
    }
    unresolved_registered = {
        token
        for item in records
        if str(item.get("code", "")) == "L5002"
        or str(item.get("code", "")).startswith("L52")
        for token in [diagnostic_token(item, full_source)]
        if token is not None
    }

    original_names = set(registered_bare_names(mutant))
    lexical_hits = registered_bare_names(candidate)
    gate_accept = (
        check_proc.returncode == 0
        and not records
        and not CODE_PATTERN.search(check_output)
    )
    excluded_removed = (
        not L52_codes
        and not unresolved_registered
        and not lexical_hits
    )
    wrong_names = sorted(trigger_names - original_names)
    wrong_substitute = bool(wrong_names)

    result: dict[str, Any] = {
        "gate_accept": gate_accept,
        "excluded_removed": excluded_removed,
        "oracle_correct": False,
        "wrong_substitute": wrong_substitute,
        "wrong_substitute_names": wrong_names,
        "original_registered_names": sorted(original_names),
        "registered_lexical_hits": lexical_hits,
        "unresolved_registered_names": sorted(unresolved_registered),
        "check_returncode": check_proc.returncode,
        "diagnostic_codes": codes,
        "band": first_code,
        "label": terminal_label(first_code),
        "run_returncode": None,
        "run_stdout": None,
        "run_stderr": None,
    }

    if gate_accept:
        run_proc = subprocess.run(
            [langl, "run", str(gated_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=RUN_TIMEOUT,
        )
        result["run_returncode"] = run_proc.returncode
        result["run_stdout"] = run_proc.stdout or ""
        result["run_stderr"] = run_proc.stderr or ""
        write_text(cell_dir / "run.stdout.txt", proc_text(run_proc.stdout))
        write_text(cell_dir / "run.stderr.txt", proc_text(run_proc.stderr))

        if run_proc.returncode != 0:
            result["label"] = 4
            result["band"] = "runtime"
        else:
            got = (run_proc.stdout or "").splitlines()
            expected = expected_lines(task["id"])
            result["oracle_correct"] = got == expected
            if result["oracle_correct"]:
                result["label"] = 6
                result["band"] = None
            else:
                result["label"] = 5
                result["band"] = "oracle"

    result["evaluation_duration_sec"] = time.monotonic() - started
    return result


def proc_text(value: str | None) -> str:
    return value or ""


def load_tasks() -> dict[str, dict[str, Any]]:
    document = json.loads(read_text(PILOT / "tasks.json"))
    return {task["id"]: task for task in document["tasks"]}


def load_r0_feedback(path: Path) -> dict[str, str]:
    value = json.loads(read_text(path))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain an object mapping case id to text")
    if not all(
        isinstance(key, str) and isinstance(payload, str)
        for key, payload in value.items()
    ):
        raise RuntimeError(f"{path} contains a non-string key or payload")
    return value


def base_result(
    case_id: str,
    task_id: str,
    condition: str,
    rep: int,
    ordinal: int,
    prompt: str,
    feedback: str,
) -> dict[str, Any]:
    return {
        "status": "running",
        "cell_id": f"rep{rep:02d}--{case_id}--{condition}",
        "case": case_id,
        "task": task_id,
        "condition": condition,
        "rep": rep,
        "ordinal": ordinal,
        "schedule_seed": SEED,
        "endpoint": "hosted Endpoint A",
        "model": MODEL,
        "model_reasoning_effort": REASONING_EFFORT,
        "feedback": feedback,
        "feedback_size": feedback_size(feedback),
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


def failed_outcomes(note: str) -> dict[str, Any]:
    return {
        "label": 1,
        "band": None,
        "note": note,
        "gate_accept": False,
        "excluded_removed": False,
        "oracle_correct": False,
        "wrong_substitute": False,
        "wrong_substitute_names": [],
        "registered_lexical_hits": [],
        "unresolved_registered_names": [],
    }


def run_cell(
    cell: tuple[int, int, str, str],
    cases: dict[str, Path],
    tasks: dict[str, dict[str, Any]],
    r0_feedback: dict[str, str],
    live_feedback: dict[str, dict[str, str]],
) -> dict[str, Any]:
    ordinal, rep, case_id, condition = cell
    case_path = cases[case_id]
    task_id = case_id.removesuffix("--capability")
    mutant = read_text(case_path)

    if condition == "C0-none":
        payload_or_none = None
        stored_feedback = ""
    elif condition == "C1-generic":
        payload_or_none = r0_feedback.get(case_id)
        if payload_or_none is None:
            payload_or_none = r0_feedback.get(task_id)
        if payload_or_none is None:
            raise RuntimeError(f"no R0 feedback for {case_id}")
        if "L5002" not in payload_or_none:
            raise RuntimeError(f"R0 feedback for {case_id} lacks L5002")
        stored_feedback = payload_or_none
    else:
        payload_or_none = live_feedback[case_id][condition]
        stored_feedback = payload_or_none

    prompt = build_prompt(mutant, payload_or_none)
    result = base_result(
        case_id,
        task_id,
        condition,
        rep,
        ordinal,
        prompt,
        stored_feedback,
    )
    result_path = RUNS / f"{result['cell_id']}.json"
    cell_dir = RUNS / result["cell_id"]
    cell_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    try:
        response, usage, model_duration, codex_rc = call_frontier(
            prompt, cell_dir
        )
        result.update(
            usage=usage,
            model_duration_sec=model_duration,
            codex_returncode=codex_rc,
            response=response,
        )
        candidate = extract_program(response)
        if candidate is None:
            result.update(failed_outcomes("empty-response"))
        elif codex_rc != 0:
            result.update(failed_outcomes(f"codex-exit-{codex_rc}"))
        else:
            result.update(
                evaluate(
                    tasks[task_id],
                    mutant,
                    candidate,
                    cell_dir,
                )
            )
        result["status"] = "complete"
    except subprocess.TimeoutExpired:
        result.update(failed_outcomes("timeout"))
        result["status"] = "complete"
    except AccountLimit as error:
        result.update(failed_outcomes(str(error)))
        result["status"] = "account-limit"
        result["duration_sec"] = time.monotonic() - started
        atomic_json(result_path, result)
        raise
    except Exception as error:
        result.update(failed_outcomes(f"{type(error).__name__}: {error}"))
        result["status"] = "error"
    result["duration_sec"] = time.monotonic() - started
    atomic_json(result_path, result)
    return result


def schedule(case_ids: list[str]) -> list[tuple[int, int, str, str]]:
    rng = random.Random(SEED)
    cells: list[tuple[int, int, str, str]] = []
    ordinal = 0
    base = [(case_id, condition) for case_id in case_ids for condition in CONDITIONS]
    for rep in range(1, REPS + 1):
        block = list(base)
        rng.shuffle(block)
        for case_id, condition in block:
            ordinal += 1
            cells.append((ordinal, rep, case_id, condition))
    return cells


def existing_complete(cell: tuple[int, int, str, str]) -> bool:
    _, rep, case_id, condition = cell
    path = RUNS / f"rep{rep:02d}--{case_id}--{condition}.json"
    if not path.exists():
        return False
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError:
        return False
    return value.get("status") == "complete"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-cells", type=int)
    parser.add_argument(
        "--r0-feedback",
        type=Path,
        default=HERE / "r0-feedback.json",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")

    RUNS.mkdir(parents=True, exist_ok=True)
    ISO.mkdir(parents=True, exist_ok=True)

    tasks = load_tasks()
    paths = sorted(CASES.glob("*--capability.l"))
    cases = {path.stem: path.resolve() for path in paths}
    expected_cases = {f"{task_id}--capability" for task_id in tasks}
    if set(cases) != expected_cases:
        missing = sorted(expected_cases - set(cases))
        extra = sorted(set(cases) - expected_cases)
        raise RuntimeError(
            f"capability population mismatch; missing={missing}, extra={extra}"
        )
    if len(cases) != 24:
        raise RuntimeError(f"expected 24 capability mutants, found {len(cases)}")

    r0_feedback = load_r0_feedback(args.r0_feedback)
    print("capturing live R0+B1 feedback for 24 mutants", flush=True)
    live_feedback = {
        case_id: policy_feedback(path) for case_id, path in cases.items()
    }

    cells = schedule(sorted(cases))
    if args.max_cells is not None:
        if args.max_cells < 0 or args.max_cells > len(cells):
            parser.error(f"--max-cells must be between 0 and {len(cells)}")
        cells = cells[: args.max_cells]

    if not args.resume:
        conflicts = [
            cell
            for cell in cells
            if (
                RUNS
                / f"rep{cell[1]:02d}--{cell[2]}--{cell[3]}.json"
            ).exists()
        ]
        if conflicts:
            raise RuntimeError(
                "result checkpoints already exist; use --resume or move "
                "seeded/repair-runs"
            )
    else:
        cells = [cell for cell in cells if not existing_complete(cell)]

    print(
        f"scheduled={len(cells)} workers={args.workers} seed={SEED}",
        flush=True,
    )
    completed = 0
    account_limited = False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                run_cell,
                cell,
                cases,
                tasks,
                r0_feedback,
                live_feedback,
            ): cell
            for cell in cells
        }
        for future in as_completed(futures):
            cell = futures[future]
            try:
                result = future.result()
                completed += 1
                print(
                    f"[{completed}/{len(cells)}] "
                    f"rep{cell[1]}/{cell[2]}/{cell[3]} "
                    f"label={result['label']} "
                    f"gate={result['gate_accept']} "
                    f"oracle={result['oracle_correct']}",
                    flush=True,
                )
            except AccountLimit:
                account_limited = True
                print("account limit detected; cancelling pending cells", flush=True)
                for pending in futures:
                    pending.cancel()
                break
            except Exception as error:
                completed += 1
                print(
                    f"CELL-ERROR rep{cell[1]}/{cell[2]}/{cell[3]}: {error}",
                    flush=True,
                )

    return 2 if account_limited else 0


if __name__ == "__main__":
    sys.exit(main())
