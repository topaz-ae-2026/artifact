"""Capture generic R0 diagnostics for the 24 capability mutants.

GATE_R0_BIN must identify a main-branch R0 executable without B1.

Usage:
    GATE_R0_BIN=... python seeded/capture_r0_feedback.py
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "r0-feedback.json"


def combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if stdout and stderr and not stdout.endswith(("\n", "\r")):
        return stdout + "\n" + stderr
    return stdout + stderr


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--langl-r0",
        default=_require_env("GATE_R0_BIN"),
        help="R0 executable, or set GATE_R0_BIN",
    )
    parser.add_argument("--cases", type=Path, default=HERE / "cases")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.langl_r0:
        parser.error("GATE_R0_BIN or --langl-r0 is required")

    cases = sorted(args.cases.glob("*--capability.l"))
    if len(cases) != 24:
        raise RuntimeError(
            f"expected 24 capability mutants in {args.cases}, found {len(cases)}"
        )

    feedback: dict[str, str] = {}
    for index, path in enumerate(cases, 1):
        proc = subprocess.run(
            [args.langl_r0, "check", str(path.resolve())],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        diagnostic = combined_output(proc)
        codes = re.findall(r"L\d{4}", diagnostic)
        if proc.returncode == 0:
            raise RuntimeError(f"{path.name}: R0 unexpectedly accepted the mutant")
        if "L5002" not in codes:
            raise RuntimeError(
                f"{path.name}: expected L5002 from R0, got {codes}"
            )
        if any(code.startswith("L52") for code in codes):
            raise RuntimeError(
                f"{path.name}: GATE_R0_BIN appears to contain B1: {codes}"
            )
        feedback[path.stem] = diagnostic
        print(f"[{index:02d}/24] {path.stem}: L5002", flush=True)

    atomic_json(args.output, feedback)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
