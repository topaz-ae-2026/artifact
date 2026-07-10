"""Corpus oracle verifier.

For every task, wraps both reference implementations in a print driver,
runs every visible and hidden case through the langl interpreter and
through Python, and requires byte-identical stdout between the two
languages. On success writes expected/<id>.visible.txt and
expected/<id>.hidden.txt (one line per case) plus a summary.

Usage: python verify_corpus.py [--langl <path-to-langl-binary>]
"""

import json
import os
import subprocess
import sys


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = os.path.dirname(os.path.abspath(__file__))
langl = _require_env("GATE_BIN")
if "--langl" in sys.argv:
    langl = sys.argv[sys.argv.index("--langl") + 1]


def driver_lines_L(task: dict, cases: list[dict]) -> list[str]:
    out = []
    fn = task["fn_L"]
    for i, c in enumerate(cases):
        args = c["L"]
        if "L_bind" in c:
            bind = c["L_bind"].replace("let e", f"let e{i}")
            out.append(bind)
            args = args.replace("e", f"e{i}") if args.strip() in ("e", "e, e", "e, 0") else args
            args = {"e": f"e{i}", "e, e": f"e{i}, e{i}", "e, 0": f"e{i}, 0"}.get(c["L"], args)
        ret = task["ret"]
        if ret == "int":
            out.append(f'print("{{{fn}({args})}}")')
        elif ret == "string":
            out.append(f"print({fn}({args}))")
        elif ret.startswith("rec:"):
            fields = ret.split(":", 1)[1].split(",")
            out.append(f"let r{i} = {fn}({args})")
            interp = " ".join("{r%d.%s}" % (i, f) for f in fields)
            out.append(f'print("{interp}")')
        else:
            raise ValueError(ret)
    return out


def driver_lines_py(task: dict, cases: list[dict]) -> list[str]:
    out = []
    fn = task["fn_py"]
    for i, c in enumerate(cases):
        args = c["py"]
        ret = task["ret"]
        if ret in ("int", "string"):
            out.append(f"print({fn}({args}))")
        elif ret.startswith("rec:"):
            fields = ret.split(":", 1)[1].split(",")
            out.append(f"_r{i} = {fn}({args})")
            interp = " ".join("{_r%d.%s}" % (i, f) for f in fields)
            out.append(f'print(f"{interp}")')
        else:
            raise ValueError(ret)
    return out


def run_L(src: str, name: str) -> list[str]:
    path = os.path.join(HERE, "_work", name + ".l")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    chk = subprocess.run([langl, "check", path], capture_output=True, text=True, encoding="utf-8")
    if chk.returncode != 0:
        raise RuntimeError(f"{name}: langl check failed\n{chk.stdout}{chk.stderr}")
    run = subprocess.run([langl, "run", path], capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        raise RuntimeError(f"{name}: langl run failed\n{run.stdout}{run.stderr}")
    return run.stdout.splitlines()


def run_py(src: str, name: str) -> list[str]:
    path = os.path.join(HERE, "_work", name + ".py")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    run = subprocess.run(
        [sys.executable, "-X", "utf8", path],
        capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )
    if run.returncode != 0:
        raise RuntimeError(f"{name}: python run failed\n{run.stdout}{run.stderr}")
    return run.stdout.splitlines()


def main() -> int:
    tasks = json.load(open(os.path.join(HERE, "tasks.json"), encoding="utf-8"))["tasks"]
    os.makedirs(os.path.join(HERE, "expected"), exist_ok=True)
    bad = 0
    for task in tasks:
        tid = task["id"]
        ref_t = open(os.path.join(HERE, "refs", "L", tid + ".l"), encoding="utf-8").read()
        ref_p = open(os.path.join(HERE, "refs", "py", tid + ".py"), encoding="utf-8").read()
        for kind in ("visible", "hidden"):
            cases = task[kind]
            src_t = ref_t + "\n" + "\n".join(driver_lines_L(task, cases)) + "\n"
            src_p = ref_p + "\n" + "\n".join(driver_lines_py(task, cases)) + "\n"
            try:
                out_t = run_L(src_t, f"{tid}.{kind}")
                out_p = run_py(src_p, f"{tid}.{kind}")
            except RuntimeError as e:
                print(f"FAIL {tid} {kind}: {e}")
                bad += 1
                continue
            if out_t != out_p:
                print(f"ORACLE-MISMATCH {tid} {kind}: L={out_t} py={out_p}")
                bad += 1
                continue
            if len(out_t) != len(cases):
                print(f"COUNT-MISMATCH {tid} {kind}: {len(out_t)} lines for {len(cases)} cases")
                bad += 1
                continue
            with open(os.path.join(HERE, "expected", f"{tid}.{kind}.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(out_t) + "\n")
        print(f"ok {tid}")
    print(f"=== corpus verify: {len(tasks)} tasks, {bad} failures ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
