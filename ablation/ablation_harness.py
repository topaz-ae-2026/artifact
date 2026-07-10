"""Specification ablation (Study C).

24 tasks x 4 language-information conditions x 3 repetitions = 288 cells,
single frontier endpoint, fresh stateless sessions, first drafts only,
no repair. Gate is the R0+B1 study compiler (langl check over the
candidate concatenated with a fixed driver on the hidden arguments).

Conditions:
  full            complete SPEC + PROFILES
  grammar-static  SPEC sections 0-21 only, no PROFILES
  examples-only   the seven public checked example programs
  none            no language-information block

Records per cell: draft-0 gate acceptance, terminal label (no repair, so
1/2/3 pre-execution, 4 runtime, 5 oracle-mismatch, 6 correct), the
diagnostic band, and a foreign-syntax-intrusion flag (parser-band or a
boundary-registry hit on an excluded idiom).

Usage: python ablation_harness.py [--workers N]
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.normpath(os.path.join(HERE, "..", "pilot"))
langl = _require_env("GATE_BIN")
CODEX = "<scrubbed>"
FRONTIER_MODEL = "gpt-5.6-sol"
langl_REPO = "<scrubbed>"
ISO = os.path.join(HERE, "_iso")
os.makedirs(ISO, exist_ok=True)

SPEC = open(os.path.join(langl_REPO, "docs/langl-v5.2/SPEC.md"), encoding="utf-8").read()
PROFILES = open(os.path.join(langl_REPO, "docs/langl-v5.2/PROFILES.md"), encoding="utf-8").read()
COND2 = open(os.path.join(HERE, "conditions", "cond2-grammar-static.md"), encoding="utf-8").read()
COND3 = open(os.path.join(HERE, "conditions", "cond3-examples-only.txt"), encoding="utf-8").read()

CONDITIONS = {
    "full": "==== LANGUAGE SPECIFICATION ====\n" + SPEC + "\n\n==== LANGUAGE PROFILES ====\n" + PROFILES,
    "grammar-static": "==== LANGUAGE SPECIFICATION (grammar and static rules) ====\n" + COND2,
    "examples-only": "==== LANGUAGE EXAMPLES ====\n" + COND3,
    "none": None,
}
REPS = 3
CALL_TIMEOUT = 420

TASKS = {t["id"]: t for t in json.load(open(os.path.join(PILOT, "tasks.json"), encoding="utf-8"))["tasks"]}


def expected_lines(tid, kind):
    return open(os.path.join(PILOT, "expected", f"{tid}.{kind}.txt"), encoding="utf-8").read().splitlines()


def driver(task, cases):
    out = []
    fn = task["fn_L"]
    for i, c in enumerate(cases):
        args = c["L"]
        if "L_bind" in c:
            out.append(c["L_bind"].replace("let e", f"let oracleE{i}"))
            args = {"e": f"oracleE{i}", "e, e": f"oracleE{i}, oracleE{i}", "e, 0": f"oracleE{i}, 0"}[c["L"]]
        ret = task["ret"]
        if ret == "int":
            out.append(f'print("{{{fn}({args})}}")')
        elif ret == "string":
            out.append(f"print({fn}({args}))")
        else:
            fields = ret.split(":", 1)[1].split(",")
            out.append(f"let oracleR{i} = {fn}({args})")
            out.append('print("' + " ".join("{oracleR%d.%s}" % (i, f) for f in fields) + '")')
    return "\n".join(out) + "\n"


def render_examples(task):
    exp = expected_lines(task["id"], "visible")
    return "\n".join(f"  {task['fn_L']}({c['L']})  ->  {e}" for c, e in zip(task["visible"], exp))


def build_prompt(task, cond):
    parts = ["You are writing a program in a small statically typed language. "
             "Define exactly the required interface. Reply with one fenced code block and nothing else."]
    info = CONDITIONS[cond]
    if info:
        parts.append(info)
    parts.append("==== TASK ====\n" + task["contract"])
    if task.get("edit"):
        base = open(os.path.join(PILOT, "bases", "L", task["id"] + ".l"), encoding="utf-8").read()
        parts.append("==== PROGRAM TO MODIFY ====\n" + base)
    parts.append("==== REQUIRED INTERFACE ====\n" + task["sig_L"])
    parts.append("==== EXAMPLES (arguments -> expected result) ====\n" + render_examples(task))
    parts.append("==== RESPONSE CONTRACT ====\nReply with exactly one fenced code block containing one "
                 "complete program that defines the required interface. No prose. Do not print; only define.")
    return "\n\n".join(parts)


CODE_BLOCK = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


def extract(text):
    b = CODE_BLOCK.findall(text)
    return b[-1].strip() + "\n" if b else None


def call_frontier(prompt, cell_dir):
    pf = os.path.join(cell_dir, "prompt.txt")
    with open(pf, "w", encoding="utf-8", newline="\n") as f:
        f.write(prompt)
    cmd = ["node", CODEX, "exec", "-c", f"model={FRONTIER_MODEL}",
           "-c", "model_reasoning_effort=medium", "-s", "read-only", "--skip-git-repo-check"]
    r = subprocess.run(cmd, stdin=open(pf, encoding="utf-8"), capture_output=True,
                       text=True, encoding="utf-8", timeout=CALL_TIMEOUT, cwd=ISO)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    with open(os.path.join(cell_dir, "response.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    return out


def gate(task, code, cell_dir):
    drv = driver(task, task["hidden"])
    gated = os.path.join(cell_dir, "gated.l")
    with open(gated, "w", encoding="utf-8", newline="\n") as f:
        f.write(code + "\n" + drv)
    chk = subprocess.run([langl, "check", gated], capture_output=True, text=True, encoding="utf-8")
    diag = (chk.stdout or "") + (chk.stderr or "")
    band = None
    m = re.search(r"L\d{4}", diag)
    if m:
        band = m.group(0)
    if chk.returncode != 0:
        # pre-execution
        if band and (band.startswith(("L0", "L1", "L2"))):
            label = 2
        else:
            label = 3
        foreign = bool(band and (band.startswith(("L0", "L1", "L2")) or band.startswith("L52")))
        return label, band, foreign, False
    run = subprocess.run([langl, "run", gated], capture_output=True, text=True,
                         encoding="utf-8", stdin=subprocess.DEVNULL)
    if run.returncode != 0:
        return 4, "runtime", False, True
    got = (run.stdout or "").splitlines()
    if got == expected_lines(task["id"], "hidden"):
        return 6, None, False, True
    return 5, "oracle", False, True


def run_cell(tid, cond, rep):
    task = TASKS[tid]
    cell_dir = os.path.join(HERE, "runs", cond, tid, f"rep{rep}")
    res = os.path.join(cell_dir, "result.json")
    if os.path.exists(res):
        return json.load(open(res, encoding="utf-8"))
    os.makedirs(cell_dir, exist_ok=True)
    prompt = build_prompt(task, cond)
    meta = {"task": tid, "cond": cond, "rep": rep, "endpoint": "hosted Endpoint A"}
    try:
        out = call_frontier(prompt, cell_dir)
    except subprocess.TimeoutExpired:
        meta.update(label=1, band=None, note="timeout", draft0_ok=False, foreign=False)
        json.dump(meta, open(res, "w", encoding="utf-8"), indent=1)
        return meta
    if "hit your session limit" in out or "usage limit" in out.lower():
        raise RuntimeError("account-limit; cell left for rerun")
    code = extract(out)
    if code is None:
        meta.update(label=1, band=None, note="no-code-block", draft0_ok=False, foreign=False)
    else:
        with open(os.path.join(cell_dir, "candidate.l"), "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        label, band, foreign, accepted = gate(task, code, cell_dir)
        meta.update(label=label, band=band, foreign=foreign, draft0_ok=accepted)
    json.dump(meta, open(res, "w", encoding="utf-8"), indent=1)
    return meta


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    cells = [(t, c, r) for c in CONDITIONS for t in TASKS for r in range(1, REPS + 1)]
    random.Random(27).shuffle(cells)
    print(f"cells: {len(cells)} workers: {workers}")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_cell, *c): c for c in cells}
        for fut, c in futs.items():
            try:
                m = fut.result()
                done += 1
                print(f"[{done}/{len(cells)}] {c[1]}/{c[0]}/rep{c[2]} -> label {m['label']} acc={m.get('draft0_ok')}", flush=True)
            except Exception as e:
                print(f"CELL-ERROR {c}: {e}", flush=True)


if __name__ == "__main__":
    main()
