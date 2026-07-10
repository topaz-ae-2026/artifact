"""Seeded-defect gate characterization (Study B).

For each of the 24 frozen reference tasks, apply per-class mutation
strategies, run every mutant through the staged pipeline, and record the
EARLIEST stage that detects it. Self-validating: a mutant is kept only
if it lands at a defect stage; equivalent mutants (output still matches
on all hidden cases) are discarded and counted as survivors. This
deliberately populates the terminal taxonomy the original pilot left
empty and shows which class escapes to the runtime and oracle stages.

Stages:
  0 extractor        (no code block)
  1 parser           (L0xxx/L1xxx/L2xxx)
  3 resolver/type    (L5002 binding, or other L5xxx type/static)
  4 capability gate  (L52xx)
  5 runtime          (check passes, run faults on a hidden input)
  6 hidden oracle    (check+run pass, output wrong on a hidden case)
  survivor           (indistinguishable from the reference)

Usage: GATE_BIN=... python seeded_defect_study.py
"""

import json
import os
import re
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
PILOT = os.path.normpath(os.path.join(HERE, "..", "pilot"))
langl = _require_env("GATE_BIN")
WORK = os.path.join(HERE, "cases")
os.makedirs(WORK, exist_ok=True)

TASKS = {t["id"]: t for t in json.load(open(os.path.join(PILOT, "tasks.json"), encoding="utf-8"))["tasks"]}


def hidden_expected(tid):
    return open(os.path.join(PILOT, "expected", f"{tid}.hidden.txt"), encoding="utf-8").read().splitlines()


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


def code_of(text):
    m = re.search(r"L\d{4}", text)
    return m.group(0) if m else None


def stage_of(mut_src, task):
    """Run the full pipeline over mutant+driver on the hidden cases and
    return (stage, detail)."""
    body = os.path.join(WORK, "cand.l")
    full = mut_src + "\n" + driver(task, task["hidden"])
    with open(body, "w", encoding="utf-8", newline="\n") as f:
        f.write(full)
    chk = subprocess.run([langl, "check", body], capture_output=True, text=True, encoding="utf-8")
    if chk.returncode != 0:
        c = code_of((chk.stdout or "") + (chk.stderr or "")) or ""
        if c.startswith(("L0", "L1", "L2")):
            return 1, c
        if c.startswith("L52"):
            return 4, c
        if c == "L5002":
            return 3, c  # binding
        if c.startswith("L5"):
            return 3, c  # type/static-semantic
        return 3, c or "reject"
    run = subprocess.run([langl, "run", body], capture_output=True, text=True,
                         encoding="utf-8", stdin=subprocess.DEVNULL)
    if run.returncode != 0:
        return 5, "runtime-fault"
    got = (run.stdout or "").splitlines()
    exp = hidden_expected(task["id"])
    if got != exp:
        return 6, "oracle-mismatch"
    return 99, "survivor"


# --- per-class mutation strategies over a reference source string ---

def mut_syntax(src):
    # drop the last closing brace -> parse error
    i = src.rfind("}")
    return src[:i] + src[i + 1:] if i >= 0 else None

def mut_binding(src, task):
    # take the first function's first parameter and rename its first
    # in-body use to an undefined non-registry name (a real binding fault)
    sig = re.search(r"function\s+\w+\s*\(\s*(\w+)\s*:", src)
    if not sig:
        return None
    param = sig.group(1)
    body_start = src.index("{", sig.end())
    body = src[body_start:]
    use = re.search(rf"(?<![A-Za-z0-9_]){re.escape(param)}(?![A-Za-z0-9_])", body)
    if not use:
        return None
    abs_at = body_start + use.start()
    return src[:abs_at] + "zz_undef_name" + src[abs_at + len(param):]

def mut_type(src):
    # flip a function return type int->string (body still returns int) -> type error
    if "-> int {" in src:
        return src.replace("-> int {", "-> string {", 1)
    if "-> string {" in src:
        return src.replace("-> string {", "-> int {", 1)
    return None

CAP_FAMILIES = ["eval", "ffi", "defmacro", "reflect", "require"]
CAP_CONTEXTS = ["value-alias", "direct-call", "template"]

def mut_capability(src, idx=0):
    # append a reachable excluded-capability request, balanced across the
    # five registry families and the three recognized source contexts by a
    # fixed task-index schedule
    name = CAP_FAMILIES[idx % len(CAP_FAMILIES)]
    ctx = CAP_CONTEXTS[idx % len(CAP_CONTEXTS)]
    if ctx == "value-alias":
        return src + '\nlet _boundary_probe = ' + name + '\nprint("{_boundary_probe}")\n'
    if ctx == "direct-call":
        return src + '\nlet _boundary_probe = ' + name + '("payload")\nprint("{_boundary_probe}")\n'
    return src + '\nprint("{' + name + '}")\n'

def mut_runtime(src):
    # widen an array loop bound by one -> index out of range at run time
    if "..< xs.length" in src:
        return src.replace("..< xs.length", "..< xs.length + 1", 1)
    if "0 ..< xs.length" in src:
        return src.replace("0 ..< xs.length", "0 ..< xs.length + 1", 1)
    return None

def mut_semantic(src):
    # flip one operator; try several, return the first that parses differently
    for a, b in [(" + ", " - "), (" - ", " + "), (" > ", " >= "), (" < ", " <= "),
                 (" * ", " + "), (" % ", " / "), (" >= ", " > "), (" <= ", " < ")]:
        if a in src:
            return src.replace(a, b, 1)
    return None


CLASSES = [
    ("syntax", 1, mut_syntax),
    ("binding", 3, mut_binding),
    ("type", 3, mut_type),
    ("capability", 4, mut_capability),
    ("runtime", 5, mut_runtime),
    ("semantic", 6, mut_semantic),
]


def main():
    records = []
    # 24 clean controls
    clean_ok = 0
    for tid, task in TASKS.items():
        ref = open(os.path.join(PILOT, "refs", "L", tid + ".l"), encoding="utf-8").read()
        st, _ = stage_of(ref, task)
        if st == 99:
            clean_ok += 1
        records.append({"task": tid, "class": "clean-control", "expected_stage": 99,
                        "achieved_stage": st, "kept": st == 99})
    # extraction-failure class: harness rule, empty candidate -> stage 0 (represented, not a program)
    for tid in TASKS:
        records.append({"task": tid, "class": "extraction", "expected_stage": 0,
                        "achieved_stage": 0, "kept": True,
                        "note": "empty or prose response, no code block, caught by the extractor"})
    # mutation classes
    for ti, (tid, task) in enumerate(TASKS.items()):
        ref = open(os.path.join(PILOT, "refs", "L", tid + ".l"), encoding="utf-8").read()
        for cname, exp_stage, fn in CLASSES:
            if cname == "binding":
                mut = fn(ref, task)
            elif cname == "capability":
                mut = fn(ref, ti)
            else:
                mut = fn(ref)
            if mut is None or mut == ref:
                records.append({"task": tid, "class": cname, "expected_stage": exp_stage,
                                "achieved_stage": None, "kept": False, "note": "no applicable single-site mutation"})
                continue
            with open(os.path.join(WORK, f"{tid}--{cname}.l"), "w", encoding="utf-8", newline="\n") as f:
                f.write(mut)
            st, detail = stage_of(mut, task)
            kept = st == exp_stage
            records.append({"task": tid, "class": cname, "expected_stage": exp_stage,
                            "achieved_stage": st, "detail": detail, "kept": kept})

    # tabulate
    by_class = {}
    for r in records:
        c = r["class"]
        by_class.setdefault(c, {"kept": 0, "total": 0, "achieved": {}})
        by_class[c]["total"] += 1
        if r["kept"]:
            by_class[c]["kept"] += 1
        a = r["achieved_stage"]
        by_class[c]["achieved"][a] = by_class[c]["achieved"].get(a, 0) + 1

    summary = {
        "tasks": len(TASKS),
        "clean_controls_survived": f"{clean_ok}/{len(TASKS)}",
        "records": len(records),
        "by_class": {c: {"kept_at_expected_stage": f"{v['kept']}/{v['total']}",
                          "achieved_stage_hist": {str(k): n for k, n in sorted(v["achieved"].items(), key=lambda x: (x[0] is None, x[0]))}}
                     for c, v in by_class.items()},
    }
    with open(os.path.join(HERE, "seeded-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"summary": summary, "records": records}, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
