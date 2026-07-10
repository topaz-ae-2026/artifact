"""Resolver-aware reclassification of the 288 stored repair cells.

The conservative lexical removal metric can count a legitimately resolved
local rebinding of a registered spelling as a failure, which is biased
against the generic-diagnostic condition. This script reclassifies every
stored cell from its recorded gate diagnostics and lexical scan, recomputes
the removal contrasts resolver-aware, and reports the C2/C3 paired
discordance and the family/context direction of the headline contrast.

Usage:
    python seeded/reclassify_removal.py
Outputs seeded/repair-reclassification.json and a stdout table.

Payload token counts in the paper use the o200k_base tokenizer; they are
shipped as precomputed constants below so replay needs no network access.
UTF-8 bytes and characters are recomputed here from the stored payloads.
"""
import collections
import glob
import json
import os
import random
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "repair-runs")
CASES = os.path.join(HERE, "cases")

FAMILY = {
    "eval": "L5201", "exec": "L5201", "compile": "L5201", "Function": "L5201",
    "ffi": "L5202", "native": "L5202", "extern": "L5202", "syscall": "L5202",
    "macro": "L5203", "defmacro": "L5203", "quote": "L5203", "unquote": "L5203",
    "reflect": "L5204", "getattr": "L5204", "setattr": "L5204", "globals": "L5204",
    "locals": "L5204", "introspect": "L5204", "require": "L5205", "dlopen": "L5205",
    "import_module": "L5205", "__import__": "L5205", "loadModule": "L5205",
}
CODE2FAM = {
    "L5201": "dynamic-evaluation", "L5202": "host-interop-ffi",
    "L5203": "macro-source-generation", "L5204": "runtime-reflection",
    "L5205": "dynamic-module-loading",
}
POLICY_CODE = re.compile(r"^[A-Z]+52\d\d$")
CONDS = ["C0-none", "C1-generic", "C2-policy-human", "C3-policy-structured"]
CONDITION_LABELS = {
    "C0-none": "C0 rejection-only",
    "C1-generic": "C1 generic-diagnostic",
    "C2-policy-human": "C2 policy-text",
    "C3-policy-structured": "C3 policy-JSON",
}
# precomputed with the o200k_base tokenizer over the stored payloads
O200K_PAYLOAD_TOKENS = {"C0-none": 0, "C1-generic": 68,
                        "C2-policy-human": 95, "C3-policy-structured": 110}


def is_policy_code(code):
    return bool(POLICY_CODE.match(code))


def load_cells():
    cells = []
    for f in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        with open(f, encoding="utf-8") as handle:
            cells.append(json.load(handle))
    if len(cells) != 288:
        raise SystemExit(f"expected 288 stored cells, found {len(cells)}")
    return cells


def mutant_meta():
    meta = {}
    ext = None
    for f in sorted(glob.glob(os.path.join(CASES, "*--capability.*"))):
        src = open(f, encoding="utf-8").read()
        tail = "\n".join(src.splitlines()[-3:])
        task = os.path.basename(f).split("--capability")[0]
        m = re.search(r"= (\w+)\(", tail)
        if m:
            meta[task] = (CODE2FAM[FAMILY[m.group(1)]], "direct-call")
            continue
        m = re.search(r"= (\w+)\s*$", tail, re.M)
        if m:
            meta[task] = (CODE2FAM[FAMILY[m.group(1)]], "value-alias")
            continue
        m = re.search(r'print\("\{(\w+)\}"\)', tail)
        if m:
            meta[task] = (CODE2FAM[FAMILY[m.group(1)]], "template")
    if len(meta) != 24:
        raise SystemExit(f"expected 24 capability mutants, found {len(meta)}")
    return meta


def classify(cell):
    codes = set(cell.get("diagnostic_codes") or [])
    policy = {c for c in codes if is_policy_code(c)}
    orig = set(cell.get("original_registered_names") or [])
    orig_codes = {FAMILY[n] for n in orig if n in FAMILY}
    # the pseudonymized tree carries the same numeric suffixes
    orig_suffix = {c[-4:] for c in orig_codes}
    if any(c[-4:] in orig_suffix for c in policy):
        return "policy-matched-remains"
    if policy:
        return "other-registered-family-substitution"
    if cell.get("excluded_removed"):
        return "removed-clean"
    if cell.get("registered_lexical_hits"):
        return "spelling-resolved-or-inert"
    return "removed-clean"


def resolver_removed(cell):
    return not any(is_policy_code(c) for c in (cell.get("diagnostic_codes") or []))


def main():
    cells = load_cells()
    meta = mutant_meta()
    tasks = sorted({c["task"] for c in cells})
    by = collections.defaultdict(list)
    for c in cells:
        by[(c["condition"], c["task"])].append(c)

    def task_mean(cond, task, fn):
        reps = by[(cond, task)]
        return sum(1.0 if fn(c) else 0.0 for c in reps) / len(reps)

    def macro(cond, fn):
        return statistics.mean(task_mean(cond, t, fn) for t in tasks)

    def contrast(cond_a, cond_b, fn, seed, draws=20000):
        diffs = [task_mean(cond_a, t, fn) - task_mean(cond_b, t, fn) for t in tasks]
        est = statistics.mean(diffs)
        rng = random.Random(seed)
        sample = sorted(
            statistics.mean(rng.choices(diffs, k=len(diffs))) for _ in range(draws)
        )
        return {
            "estimate_pp": round(est * 100, 1),
            "ci95_pp": [round(sample[int(0.025 * (draws - 1))] * 100, 1),
                        round(sample[int(0.975 * (draws - 1))] * 100, 1)],
        }

    reclass = {cond: collections.Counter() for cond in CONDS}
    for c in cells:
        reclass[c["condition"]][classify(c)] += 1

    means = {cond: round(macro(cond, resolver_removed) * 100, 1) for cond in CONDS}
    contrasts = {
        "C2_minus_C1": contrast("C2-policy-human", "C1-generic", resolver_removed, 52027),
        "C1_minus_C0": contrast("C1-generic", "C0-none", resolver_removed, 52127),
        "C3_minus_C2": contrast("C3-policy-structured", "C2-policy-human", resolver_removed, 52227),
    }

    def cellmap(cond):
        return {(c["task"], c["rep"]): c for c in cells if c["condition"] == cond}

    c2m, c3m = cellmap("C2-policy-human"), cellmap("C3-policy-structured")
    discordance = {}
    for name, fn in (
        ("resolver_removed", resolver_removed),
        ("other_family_substitution", lambda c: bool(c["wrong_substitute"])),
        ("oracle_correct", lambda c: bool(c["oracle_correct"])),
    ):
        q = collections.Counter()
        for k in sorted(c2m):
            a, b = fn(c2m[k]), fn(c3m[k])
            key = "both" if a and b else "C2-only" if a else "C3-only" if b else "neither"
            q[key] += 1
        discordance[name] = dict(q)

    breakdown = {"family": {}, "context": {}}
    for dim, idx in (("family", 0), ("context", 1)):
        groups = collections.defaultdict(list)
        for t in tasks:
            groups[meta[t][idx]].append(t)
        for g, ts in sorted(groups.items()):
            d2 = statistics.mean(task_mean("C2-policy-human", t, resolver_removed) for t in ts)
            d1 = statistics.mean(task_mean("C1-generic", t, resolver_removed) for t in ts)
            breakdown[dim][g] = {"n_tasks": len(ts), "C2_minus_C1_pp": round((d2 - d1) * 100, 1)}

    payloads = {}
    for cond in CONDS:
        fbs = [c.get("feedback") or "" for c in cells if c["condition"] == cond]
        payloads[cond] = {
            "o200k_tokens_precomputed": O200K_PAYLOAD_TOKENS[cond],
            "utf8_bytes_mean": round(statistics.mean(len(x.encode("utf-8")) for x in fbs)),
            "chars_mean": round(statistics.mean(len(x) for x in fbs)),
        }

    result = {
        "definition": {
            "resolver_removed": "the stored post-repair gate run emits no policy-family diagnostic",
            "note": "a parse-rejected repair trivially emits none and is captured separately by gate acceptance",
        },
        "condition_labels": CONDITION_LABELS,
        "reclassification_counts": {c: dict(reclass[c]) for c in CONDS},
        "resolver_removed_taskmacro_pct": means,
        "resolver_removed_contrasts": contrasts,
        "c2_c3_paired_discordance": discordance,
        "c2_c1_breakdown": breakdown,
        "payload_sizes": payloads,
        "bootstrap": {"draws": 20000, "seeds": [52027, 52127, 52227]},
    }
    out = os.path.join(HERE, "repair-reclassification.json")
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=1)
    print(json.dumps(result, indent=1))
    print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
