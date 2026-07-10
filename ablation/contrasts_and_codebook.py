"""Paired-task-bootstrap contrast CIs (acceptance and correctness) and a
foreign-idiom codebook for the no-information rejections."""

import json
import os
import random
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.normpath(os.path.join(HERE, "..", "pilot"))
TASKS = [t["id"] for t in json.load(open(os.path.join(PILOT, "tasks.json"), encoding="utf-8"))["tasks"]]
CONDS = ["grammar-static", "examples-only", "none"]
REPS = (1, 2, 3)


def cells():
    out = []
    for c in ["full"] + CONDS:
        for t in TASKS:
            for r in REPS:
                p = os.path.join(HERE, "runs", c, t, f"rep{r}", "result.json")
                if os.path.exists(p):
                    out.append(json.load(open(p, encoding="utf-8")))
    return out


def task_mean(data, cond, t, pred):
    sub = [x for x in data if x["cond"] == cond and x["task"] == t]
    return sum(1 for x in sub if pred(x)) / len(sub) if sub else None


def paired_contrast(data, cond, pred, tasks):
    diffs = []
    for t in tasks:
        a = task_mean(data, cond, t, pred)
        b = task_mean(data, "full", t, pred)
        if a is not None and b is not None:
            diffs.append(a - b)
    return statistics.mean(diffs) if diffs else float("nan")


def boot_contrast(data, cond, pred, n=10000, seed=27):
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        s = [TASKS[rng.randrange(len(TASKS))] for _ in TASKS]
        vals.append(paired_contrast(data, cond, pred, s))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n)]


def pp(x):
    return round(100 * x, 1)


ACC = lambda x: x.get("draft0_ok")
COR = lambda x: x["label"] == 6

# foreign-idiom codebook patterns (host-language tells)
IDIOMS = [
    ("semicolon-terminator", re.compile(r";\s*$", re.M)),
    ("ternary-then-else", re.compile(r"\bif\b[^\n]*\bthen\b[^\n]*\belse\b")),
    ("c-style-for-paren", re.compile(r"\bfor\s*\(")),
    ("paren-condition", re.compile(r"\bif\s*\(")),
    ("while-paren", re.compile(r"\bwhile\s*\(")),
    ("python-def", re.compile(r"\bdef\s+\w+\s*\(")),
    ("rust-fn", re.compile(r"\bfn\s+\w+\s*\(")),
    ("arrow-lambda", re.compile(r"=>")),
    ("js-const-var", re.compile(r"\b(const|var)\s+\w+\s*=")),
    ("cpp-include-import", re.compile(r"#include|\bimport\s+\w+")),
]


def main():
    data = cells()
    print("=== paired-task-bootstrap contrasts vs full (percentage points) ===")
    print(f"{'condition':16} {'acceptance dela [95% CI]':30} {'correctness dela [95% CI]'}")
    table = {}
    for c in CONDS:
        a = pp(paired_contrast(data, c, ACC, TASKS)); aci = boot_contrast(data, c, ACC)
        k = pp(paired_contrast(data, c, COR, TASKS)); kci = boot_contrast(data, c, COR)
        table[c] = {"acc_delta": a, "acc_ci": [pp(aci[0]), pp(aci[1])],
                    "cor_delta": k, "cor_ci": [pp(kci[0]), pp(kci[1])]}
        print(f"{c:16} {a:+6} [{pp(aci[0]):+},{pp(aci[1]):+}]        {k:+6} [{pp(kci[0]):+},{pp(kci[1]):+}]")

    # codebook over none-condition label-2 rejections
    print("\n=== foreign-idiom codebook: none-condition parser-band rejections ===")
    rows = []
    for t in TASKS:
        for r in REPS:
            p = os.path.join(HERE, "runs", "none", t, f"rep{r}")
            res = os.path.join(p, "result.json")
            if not os.path.exists(res):
                continue
            m = json.load(open(res, encoding="utf-8"))
            if m.get("label") != 2:
                continue
            cand = os.path.join(p, "candidate.l")
            code = open(cand, encoding="utf-8").read() if os.path.exists(cand) else ""
            tags = [name for name, pat in IDIOMS if pat.search(code)]
            rows.append({"task": t, "rep": r, "band": m.get("band"), "idioms": tags})
    from collections import Counter
    tally = Counter()
    for row in rows:
        for tag in (row["idioms"] or ["unclassified"]):
            tally[tag] += 1
    print(f"total parser-band (label-2) rejections: {len(rows)}")
    for tag, n in tally.most_common():
        print(f"  {tag:22} {n}")
    unclassified = [r for r in rows if not r["idioms"]]
    print(f"unclassified: {len(unclassified)}  -> {[r['task'] for r in unclassified]}")

    json.dump({"contrasts": table, "intrusion_rows": rows,
               "intrusion_tally": dict(tally), "total_label2": len(rows)},
              open(os.path.join(HERE, "contrasts-codebook.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
