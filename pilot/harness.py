"""LMPL 2026 pilot harness.

Runs 2 agents x 24 tasks x 2 languages x 3 repetitions. Every cell:
generate one first draft, apply the typed gate to candidate+driver,
repair only gate-rejected candidates (at most 3 rounds, raw diagnostic
only), then run hidden checks once on the first gate-accepted candidate.
All artifacts are recorded under runs/. Cells already holding a
result.json are skipped, so the harness is resumable.

Terminal labels:
  1 response-contract failure (no extractable code block)
  2 pre-execution lexical or syntactic rejection
  3 pre-execution binding, type, or static-semantic rejection
  4 gate accepted, execution exception or timeout
  5 gate accepted, clean execution, oracle mismatch
  6 gate accepted, all hidden checks correct
Labels 2/3 are the label of the LAST gate event when repair is
exhausted (censored). Draft-0 py_compile acceptance is recorded as a
separate counterfactual reading and never drives repair.
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
langl = _require_env("GATE_BIN")
FRONTIER_CLI = os.environ.get("FRONTIER_CLI", "redacted")
langl_REPO = "<scrubbed>"
SPEC = open(os.path.join(langl_REPO, "docs/langl-v5.2/SPEC.md"), encoding="utf-8").read()
PROFILES = open(os.path.join(langl_REPO, "docs/langl-v5.2/PROFILES.md"), encoding="utf-8").read()
ISOLATED = os.path.join(HERE, "_isolated")
os.makedirs(ISOLATED, exist_ok=True)

AGENTS = {
    "author-frontier": {"model": os.environ.get("FRONTIER_MODEL", "redacted"), "effort": "medium", "cli": "redacted-cli"},
    "author-compact": {"model": os.environ.get("COMPACT_MODEL", "redacted"), "cli": "redacted-cli"},
}
REPS = 3
CALL_TIMEOUT = 420
RUN_TIMEOUT = 30
MAX_REPAIRS = 3

TASKS = {t["id"]: t for t in json.load(open(os.path.join(HERE, "tasks.json"), encoding="utf-8"))["tasks"]}


def expected_lines(tid: str, kind: str) -> list[str]:
    return open(os.path.join(HERE, "expected", f"{tid}.{kind}.txt"), encoding="utf-8").read().splitlines()


def driver_L(task: dict, cases: list[dict]) -> str:
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


def driver_py(task: dict, cases: list[dict]) -> str:
    out = []
    fn = task["fn_py"]
    for i, c in enumerate(cases):
        args = c["py"]
        ret = task["ret"]
        if ret in ("int", "string"):
            out.append(f"print({fn}({args}))")
        else:
            fields = ret.split(":", 1)[1].split(",")
            out.append(f"oracle_r{i} = {fn}({args})")
            out.append('print(f"' + " ".join("{oracle_r%d.%s}" % (i, f) for f in fields) + '")')
    return "\n".join(out) + "\n"


def render_examples(task: dict) -> str:
    exp = expected_lines(task["id"], "visible")
    lines = []
    for c, e in zip(task["visible"], exp):
        lines.append(f"  {task['fn_L']}({c['L']})  ->  {e}")
    return "\n".join(lines)


def build_prompt(task: dict, lang: str) -> str:
    parts = []
    if lang == "L":
        parts.append("You are writing a program in the langl language. The complete normative specification and profile material follow. Use only what they define.")
        parts.append("==== langl SPEC ====\n" + SPEC)
        parts.append("==== langl PROFILES ====\n" + PROFILES)
    else:
        parts.append("You are writing Python 3.12. Use only the language itself and, when a prelude is shown, that prelude. No imports other than the ones in the prelude. The code must pass mypy --strict.")
    parts.append("==== TASK ====\n" + task["contract"])
    if task.get("edit"):
        base = open(os.path.join(HERE, "bases", lang, task["id"] + (".l" if lang == "L" else ".py")), encoding="utf-8").read()
        parts.append("==== PROGRAM TO MODIFY ====\n" + base)
    sig = task["sig_L"] if lang == "L" else task["sig_py"]
    parts.append("==== REQUIRED INTERFACE ====\n" + sig)
    if lang == "py" and "py_prelude" in task:
        parts.append("==== PROVIDED PRELUDE (include it verbatim at the top of your program) ====\n" + task["py_prelude"])
    parts.append("==== EXAMPLES (arguments -> expected result) ====\n" + render_examples(task))
    lang_word = "langl" if lang == "L" else "Python"
    parts.append(f"==== RESPONSE CONTRACT ====\nReply with exactly one fenced code block containing one complete {lang_word} program that defines the required interface. No prose outside the code block. Do not print anything; only define the function(s).")
    return "\n\n".join(parts)


CODE_BLOCK = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str | None:
    blocks = CODE_BLOCK.findall(text)
    return blocks[-1].strip() + "\n" if blocks else None


def call_agent(agent: str, prompt: str, cell_dir: str, round_no: int) -> tuple[str, float]:
    pf = os.path.join(cell_dir, f"prompt{round_no}.txt")
    with open(pf, "w", encoding="utf-8", newline="\n") as f:
        f.write(prompt)
    t0 = time.time()
    if agent == "author-frontier":
        cmd = ["node", FRONTIER_CLI, "exec", "-c", f"model={AGENTS['author-frontier']['model']}",
               "-c", f"model_reasoning_effort={AGENTS['author-frontier']['effort']}", "-s", "read-only",
               "--skip-git-repo-check"]
        r = subprocess.run(cmd, stdin=open(pf, encoding="utf-8"), capture_output=True,
                           text=True, encoding="utf-8", timeout=CALL_TIMEOUT, cwd=ISOLATED)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
    else:
        cmd = [os.environ.get("COMPACT_CLI", "redacted"), "-p", "--model", AGENTS["author-compact"]["model"]]
        r = subprocess.run(cmd, stdin=open(pf, encoding="utf-8"), capture_output=True,
                           text=True, encoding="utf-8", timeout=CALL_TIMEOUT, cwd=ISOLATED, shell=True)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
    dt = time.time() - t0
    with open(os.path.join(cell_dir, f"response{round_no}.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    return out, dt


def gate_L(path: str) -> tuple[bool, str, int]:
    r = subprocess.run([langl, "check", path], capture_output=True, text=True, encoding="utf-8", timeout=60)
    diag = (r.stdout or "") + (r.stderr or "")
    if r.returncode == 0:
        return True, diag, 0
    codes = re.findall(r"L(\d)\d{3}", diag)
    cat = 2 if codes and codes[0] in ("0", "1", "2") else 3
    return False, diag, cat


def gate_py(path: str) -> tuple[bool, str, int, bool]:
    c = subprocess.run([sys.executable, "-X", "utf8", "-m", "py_compile", path],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    compile_ok = c.returncode == 0
    if not compile_ok:
        return False, (c.stdout or "") + (c.stderr or ""), 2, False
    m = subprocess.run([sys.executable, "-X", "utf8", "-m", "mypy", "--strict", "--no-error-summary",
                        "--cache-dir", os.path.join(HERE, "_mypy_cache"), path],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    diag = (m.stdout or "") + (m.stderr or "")
    if m.returncode == 0:
        return True, diag, 0, True
    cat = 2 if "[syntax]" in diag else 3
    return False, diag, cat, True


def run_oracle(task: dict, lang: str, candidate_path: str, cell_dir: str) -> tuple[int, str]:
    hidden = task["hidden"]
    exp = expected_lines(task["id"], "hidden")
    if lang == "L":
        r = subprocess.run([langl, "run", candidate_path], capture_output=True, text=True,
                           encoding="utf-8", timeout=RUN_TIMEOUT)
    else:
        r = subprocess.run([sys.executable, "-X", "utf8", candidate_path], capture_output=True,
                           text=True, encoding="utf-8", timeout=RUN_TIMEOUT, stdin=subprocess.DEVNULL)
    out = (r.stdout or "")
    with open(os.path.join(cell_dir, "oracle.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"exit={r.returncode}\n--- stdout ---\n{out}\n--- stderr ---\n{r.stderr or ''}")
    if r.returncode != 0:
        return 4, "execution-failure"
    got = out.splitlines()
    return (6, "correct") if got == exp else (5, f"mismatch got={got[:8]}")


def run_cell(agent: str, tid: str, lang: str, rep: int) -> dict:
    task = TASKS[tid]
    cell_dir = os.path.join(HERE, "runs", agent, lang, tid, f"rep{rep}")
    res_path = os.path.join(cell_dir, "result.json")
    if os.path.exists(res_path):
        return json.load(open(res_path, encoding="utf-8"))
    os.makedirs(cell_dir, exist_ok=True)
    ext = ".l" if lang == "L" else ".py"
    drv = driver_L(task, task["hidden"]) if lang == "L" else driver_py(task, task["hidden"])
    meta = {"agent": agent, "model": AGENTS[agent]["model"], "cli": AGENTS[agent]["cli"],
            "task": tid, "lang": lang, "rep": rep, "rounds": [], "started": time.time()}
    if agent == "author-frontier":
        meta["effort"] = AGENTS["author-frontier"]["effort"]
    prompt = build_prompt(task, lang)
    label, note, py_compile0 = None, "", None
    for rnd in range(0, MAX_REPAIRS + 1):
        try:
            out, dt = call_agent(agent, prompt, cell_dir, rnd)
        except subprocess.TimeoutExpired:
            label, note = 1, "agent-timeout"
            meta["rounds"].append({"round": rnd, "event": "agent-timeout"})
            break
        if "hit your session limit" in out or "usage limit" in out.lower():
            raise RuntimeError("account-limit-refusal, cell left unrecorded for rerun")
        code = extract_code(out)
        if code is None:
            label, note = 1, "no-code-block"
            meta["rounds"].append({"round": rnd, "event": "no-code-block", "secs": round(dt, 1)})
            break
        cand = os.path.join(cell_dir, f"candidate{rnd}{ext}")
        with open(cand, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        gated = os.path.join(cell_dir, f"gated{rnd}{ext}")
        with open(gated, "w", encoding="utf-8", newline="\n") as f:
            f.write(code + "\n" + drv)
        if lang == "L":
            ok, diag, cat = gate_L(gated)
        else:
            ok, diag, cat, compiled = gate_py(gated)
            if rnd == 0:
                py_compile0 = compiled
        with open(os.path.join(cell_dir, f"gate{rnd}.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(diag)
        meta["rounds"].append({"round": rnd, "event": "gate-ok" if ok else f"gate-reject-cat{cat}", "secs": round(dt, 1)})
        if ok:
            label, note = run_oracle(task, lang, gated, cell_dir)
            meta["accepted_round"] = rnd
            break
        if rnd == MAX_REPAIRS:
            label, note = cat, "censored-after-3-repairs"
            break
        prompt = (build_prompt(task, lang)
                  + "\n\n==== YOUR PREVIOUS ANSWER ====\n" + code
                  + "\n\n==== TOOLCHAIN DIAGNOSTIC ====\n" + diag
                  + "\n\nThe toolchain rejected the candidate above. Reply with exactly one fenced code block containing the corrected complete program. No prose.")
    meta["label"] = label
    meta["note"] = note
    meta["py_compile_draft0"] = py_compile0
    meta["finished"] = time.time()
    with open(res_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=1)
    return meta


def main() -> None:
    only_agent = sys.argv[sys.argv.index("--agent") + 1] if "--agent" in sys.argv else None
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    cells = [(a, t, l, r) for a in AGENTS for t in TASKS for l in ("L", "py") for r in range(1, REPS + 1)
             if only_agent in (None, a)]
    random.Random(26).shuffle(cells)
    print(f"cells: {len(cells)} workers: {workers}")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_cell, *c): c for c in cells}
        for fut in futs:
            pass
        for fut, c in futs.items():
            try:
                m = fut.result()
                done += 1
                print(f"[{done}/{len(cells)}] {c[0]}/{c[2]}/{c[1]}/rep{c[3]} -> label {m['label']} ({m['note']})", flush=True)
            except Exception as e:
                print(f"CELL-ERROR {c}: {e}", flush=True)


if __name__ == "__main__":
    main()
