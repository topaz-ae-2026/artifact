"""Analyze the specification ablation. Task-macro means with task-cluster
bootstrap 95 percent intervals, per condition."""

import json
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.normpath(os.path.join(HERE, "..", "pilot"))
TASKS = [t["id"] for t in json.load(open(os.path.join(PILOT, "tasks.json"), encoding="utf-8"))["tasks"]]
CONDS = ["full", "grammar-static", "examples-only", "none"]
REPS = (1, 2, 3)


def load():
    cells = []
    for c in CONDS:
        for t in TASKS:
            for r in REPS:
                p = os.path.join(HERE, "runs", c, t, f"rep{r}", "result.json")
                if os.path.exists(p):
                    cells.append(json.load(open(p, encoding="utf-8")))
    return cells


def macro(cells, cond, pred, tasks=None):
    tasks = tasks or TASKS
    vals = []
    for t in tasks:
        sub = [c for c in cells if c["cond"] == cond and c["task"] == t]
        if sub:
            vals.append(sum(1 for c in sub if pred(c)) / len(sub))
    return statistics.mean(vals) if vals else float("nan")


def boot(cells, cond, pred, n=10000, seed=27):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        s = [TASKS[rng.randrange(len(TASKS))] for _ in TASKS]
        out.append(macro(cells, cond, pred, s))
    out.sort()
    return out[int(0.025 * n)], out[int(0.975 * n)]


def pct(x):
    return round(100 * x, 1)


def main():
    cells = load()
    labels = (1, 2, 3, 4, 5, 6)
    summary = {"cells": len(cells), "conditions": {}}
    print(f"{'condition':16} {'draft0-accept':>16} {'correct(6)':>16} {'foreign%':>9}  label-dist(1..6)")
    for c in CONDS:
        sub = [x for x in cells if x["cond"] == c]
        acc = macro(cells, c, lambda x: x.get("draft0_ok"))
        acc_ci = boot(cells, c, lambda x: x.get("draft0_ok"))
        corr = macro(cells, c, lambda x: x["label"] == 6)
        corr_ci = boot(cells, c, lambda x: x["label"] == 6)
        foreign = macro(cells, c, lambda x: x.get("foreign"))
        dist = {l: sum(1 for x in sub if x["label"] == l) for l in labels}
        summary["conditions"][c] = {
            "n": len(sub),
            "draft0_accept": pct(acc), "draft0_ci": [pct(acc_ci[0]), pct(acc_ci[1])],
            "correct": pct(corr), "correct_ci": [pct(corr_ci[0]), pct(corr_ci[1])],
            "foreign_intrusion": pct(foreign),
            "label_dist": dist,
        }
        print(f"{c:16} {pct(acc):6} [{pct(acc_ci[0])},{pct(acc_ci[1])}]  {pct(corr):6} [{pct(corr_ci[0])},{pct(corr_ci[1])}]  {pct(foreign):7}  {dist}")

    # contrasts vs full
    print("\n=== task-macro contrasts (condition minus full), draft0-accept ===")
    for c in CONDS:
        if c == "full":
            continue
        d = [macro([x for x in cells if x['task']==t], c, lambda x: x.get('draft0_ok'), [t]) -
             macro([x for x in cells if x['task']==t], 'full', lambda x: x.get('draft0_ok'), [t]) for t in TASKS]
        print(f"  {c:16} delta = {pct(statistics.mean(d)):+6}  (per-task mean)")

    json.dump(summary, open(os.path.join(HERE, "ablation-summary.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
