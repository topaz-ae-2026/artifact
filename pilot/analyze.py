"""Pilot analysis. Reads runs/**/result.json, writes results.csv,
summary.json, and generated/pilot-tables.tex.

Reporting follows the frozen protocol: each agent shown separately,
macro-average over tasks (repetitions never inflate n), task-cluster
bootstrap percentile intervals, joint reporting of gate acceptance,
accepted-and-correct yield, post-acceptance escape, the six-category
outcome distribution, cumulative acceptance by repair round, and the
draft-0 py_compile counterfactual.
"""

import csv
import json
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = {t["id"]: t for t in json.load(open(os.path.join(HERE, "tasks.json"), encoding="utf-8"))["tasks"]}
AGENTS = ("author-frontier", "author-compact")
LANGS = ("L", "py")
REPS = (1, 2, 3)
LABELS = (1, 2, 3, 4, 5, 6)


def load_cells() -> list[dict]:
    cells = []
    for a in AGENTS:
        for l in LANGS:
            for t in TASKS:
                for r in REPS:
                    p = os.path.join(HERE, "runs", a, l, t, f"rep{r}", "result.json")
                    if not os.path.exists(p):
                        continue
                    m = json.load(open(p, encoding="utf-8"))
                    d0 = m["rounds"][0]["event"] if m["rounds"] else "missing"
                    gate0 = os.path.join(HERE, "runs", a, l, t, f"rep{r}", "gate0.txt")
                    diag0 = open(gate0, encoding="utf-8").read() if os.path.exists(gate0) else ""
                    unresolved = ("L5002" in diag0) if l == "L" else (
                        "[name-defined]" in diag0 or "[attr-defined]" in diag0)
                    cells.append({
                        "agent": a, "lang": l, "task": t, "rep": r,
                        "stratum": TASKS[t]["stratum"], "label": m["label"],
                        "accepted_round": m.get("accepted_round", None),
                        "draft0_ok": d0 == "gate-ok",
                        "py_compile_draft0": m.get("py_compile_draft0"),
                        "unresolved_draft0": unresolved,
                        "rounds_run": len(m["rounds"]),
                    })
    return cells


def macro(cells: list[dict], pred, tasks=None) -> float:
    tasks = tasks or list(TASKS)
    vals = []
    for t in tasks:
        sub = [c for c in cells if c["task"] == t]
        if sub:
            vals.append(sum(1 for c in sub if pred(c)) / len(sub))
    return statistics.mean(vals) if vals else float("nan")


def boot_ci(cells: list[dict], pred, n=10000, seed=26) -> tuple[float, float]:
    rng = random.Random(seed)
    tasks = list(TASKS)
    stats = []
    for _ in range(n):
        sample = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        stats.append(macro(cells, pred, tasks=sample))
    stats.sort()
    return stats[int(0.025 * n)], stats[int(0.975 * n)]


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def main() -> None:
    cells = load_cells()
    print(f"cells loaded: {len(cells)}")
    os.makedirs(os.path.join(HERE, "generated"), exist_ok=True)

    with open(os.path.join(HERE, "results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cells[0].keys()))
        w.writeheader()
        w.writerows(cells)

    summary: dict = {"cells": len(cells)}
    lines_main = []
    lines_dist = []
    for a in AGENTS:
        for l in LANGS:
            sub = [c for c in cells if c["agent"] == a and c["lang"] == l]
            if not sub:
                continue
            key = f"{a}-{l}"
            d0 = macro(sub, lambda c: c["draft0_ok"])
            d0_lo, d0_hi = boot_ci(sub, lambda c: c["draft0_ok"])
            yield6 = macro(sub, lambda c: c["label"] == 6)
            y_lo, y_hi = boot_ci(sub, lambda c: c["label"] == 6)
            acc = [c for c in sub if c["accepted_round"] is not None]
            escape = (sum(1 for c in acc if c["label"] in (4, 5)) / len(acc)) if acc else float("nan")
            cum = {r: macro(sub, lambda c, r=r: c["accepted_round"] is not None and c["accepted_round"] <= r)
                   for r in (0, 1, 2, 3)}
            dist = {lab: sum(1 for c in sub if c["label"] == lab) for lab in LABELS}
            unres = macro(sub, lambda c: c["unresolved_draft0"])
            pyc = None
            if l == "py":
                known = [c for c in sub if c["py_compile_draft0"] is not None]
                pyc = macro(known, lambda c: bool(c["py_compile_draft0"])) if known else None
            summary[key] = {
                "n": len(sub), "draft0_gate_acceptance": d0, "draft0_ci": [d0_lo, d0_hi],
                "accepted_and_correct": yield6, "yield_ci": [y_lo, y_hi],
                "post_acceptance_escape": escape, "cumulative_acceptance": cum,
                "outcome_distribution": dist, "unresolved_draft0_rate": unres,
                "py_compile_draft0": pyc,
            }
            gate_name = "langl check" if l == "L" else "py\\_compile + mypy --strict"
            agent_name = "Frontier author" if a == "author-frontier" else "Compact author"
            lang_name = "langl" if l == "L" else "Python"
            lines_main.append(
                f"{agent_name} & {lang_name} & {pct(d0)} [{pct(d0_lo)}, {pct(d0_hi)}] & "
                f"{pct(cum[3])} & {pct(yield6)} [{pct(y_lo)}, {pct(y_hi)}] & {pct(escape)} \\\\")
            lines_dist.append(
                f"{agent_name} & {lang_name} & " + " & ".join(str(dist[lab]) for lab in LABELS) + " \\\\")

    strata = sorted({t["stratum"] for t in TASKS.values()})
    lines_strata = []
    for s in strata:
        stasks = [tid for tid, t in TASKS.items() if t["stratum"] == s]
        row = [s]
        for a in AGENTS:
            for l in LANGS:
                sub = [c for c in cells if c["agent"] == a and c["lang"] == l and c["task"] in stasks]
                row.append(pct(macro(sub, lambda c: c["label"] == 6, tasks=stasks)) if sub else "-")
        lines_strata.append(" & ".join(row) + " \\\\")

    with open(os.path.join(HERE, "summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
    with open(os.path.join(HERE, "generated", "pilot-tables.tex"), "w", encoding="utf-8", newline="\n") as f:
        f.write("% generated by analyze.py, do not edit\n")
        f.write("% MAIN: agent & lang & draft0 acceptance [CI] & cum-accept r3 & correct yield [CI] & escape\n")
        f.write("\n".join(lines_main) + "\n\n")
        f.write("% DIST: agent & lang & label1..label6 counts\n")
        f.write("\n".join(lines_dist) + "\n\n")
        f.write("% STRATA: stratum & frontier-L & frontier-py & compact-L & compact-py (label-6 macro %)\n")
        f.write("\n".join(lines_strata) + "\n")
    print(json.dumps(summary, indent=1)[:3000])


if __name__ == "__main__":
    main()
