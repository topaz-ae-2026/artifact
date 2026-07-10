"""Analyze Study D repair-ablation checkpoints.

Repetitions are averaged within task and condition. Contrasts then resample
paired tasks, preserving the 24-task unit of inference.

Usage:
    python seeded/analyze_repair_ablation.py
    python seeded/analyze_repair_ablation.py --bootstrap 50000
"""

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_RUNS = HERE / "repair-runs"
DEFAULT_OUTPUT = HERE / "repair-ablation-analysis.json"

CONDITIONS = (
    "C0-none",
    "C1-generic",
    "C2-policy-human",
    "C3-policy-structured",
)
OUTCOMES = (
    "gate_accept",
    "excluded_removed",
    "oracle_correct",
    "wrong_substitute",
)
COSTS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "model_duration_sec",
    "duration_sec",
    "feedback_chars",
    "feedback_utf8_bytes",
    "feedback_lines",
    "feedback_whitespace_tokens",
)
CONTRASTS = (
    ("C2-policy-human", "C1-generic"),
    ("C3-policy-structured", "C2-policy-human"),
    ("C1-generic", "C0-none"),
)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def metric_value(record: dict[str, Any], metric: str) -> float | None:
    if metric in OUTCOMES:
        value = record.get(metric)
        return float(value) if isinstance(value, bool) else None

    if metric in (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
    ):
        usage = record.get("usage")
        value = usage.get(metric) if isinstance(usage, dict) else None
    elif metric.startswith("feedback_"):
        sizes = record.get("feedback_size")
        key = metric.removeprefix("feedback_")
        value = sizes.get(key) if isinstance(sizes, dict) else None
    else:
        value = record.get(metric)

    if type(value) in (int, float) and math.isfinite(float(value)):
        return float(value)
    return None


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("empty percentile input")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight
    )


def paired_bootstrap(
    left: dict[str, float],
    right: dict[str, float],
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    tasks = sorted(set(left) & set(right))
    if not tasks:
        return {
            "estimate": None,
            "ci95": [None, None],
            "paired_tasks": 0,
        }

    differences = [left[task] - right[task] for task in tasks]
    estimate = statistics.fmean(differences)
    rng = random.Random(seed)
    draws = []
    for _ in range(iterations):
        draws.append(
            statistics.fmean(
                differences[rng.randrange(len(differences))]
                for _ in differences
            )
        )
    draws.sort()
    return {
        "estimate": estimate,
        "ci95": [
            percentile(draws, 0.025),
            percentile(draws, 0.975),
        ],
        "paired_tasks": len(tasks),
    }


def fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{100.0 * value:6.1f}"


def fmt_number(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=52027)
    args = parser.parse_args()
    if args.bootstrap < 1:
        parser.error("--bootstrap must be positive")

    records = []
    ignored = []
    for path in sorted(args.runs.glob("*.json")):
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError):
            ignored.append({"path": str(path), "reason": "unreadable"})
            continue
        if record.get("status") != "complete":
            ignored.append(
                {
                    "path": str(path),
                    "reason": str(record.get("status", "missing-status")),
                }
            )
            continue
        if (
            record.get("condition") not in CONDITIONS
            or not isinstance(record.get("task"), str)
        ):
            ignored.append({"path": str(path), "reason": "not-a-cell"})
            continue
        records.append(record)

    if not records:
        raise RuntimeError(f"no completed cell records in {args.runs}")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record["task"], record["condition"])].append(record)

    task_means: dict[str, dict[str, dict[str, float | None]]] = defaultdict(dict)
    for (task, condition), cells in grouped.items():
        values: dict[str, float | None] = {}
        for metric in OUTCOMES + COSTS:
            observed = [
                value
                for cell in cells
                for value in [metric_value(cell, metric)]
                if value is not None
            ]
            values[metric] = mean(observed)
        values["repetitions"] = float(len(cells))
        task_means[task][condition] = values

    condition_summary: dict[str, dict[str, Any]] = {}
    for condition in CONDITIONS:
        task_rows = [
            conditions[condition]
            for conditions in task_means.values()
            if condition in conditions
        ]
        summary: dict[str, Any] = {
            "tasks": len(task_rows),
            "cells": sum(
                len(cells)
                for (task, candidate), cells in grouped.items()
                if candidate == condition
            ),
        }
        for metric in OUTCOMES + COSTS:
            observed = [
                float(row[metric])
                for row in task_rows
                if row.get(metric) is not None
            ]
            summary[metric] = mean(observed)
        condition_summary[condition] = summary

    contrasts: dict[str, dict[str, Any]] = {}
    for contrast_index, (left_condition, right_condition) in enumerate(
        CONTRASTS
    ):
        label = f"{left_condition}_minus_{right_condition}"
        contrasts[label] = {}
        for metric_index, metric in enumerate(OUTCOMES):
            left = {
                task: float(conditions[left_condition][metric])
                for task, conditions in task_means.items()
                if left_condition in conditions
                and conditions[left_condition].get(metric) is not None
            }
            right = {
                task: float(conditions[right_condition][metric])
                for task, conditions in task_means.items()
                if right_condition in conditions
                and conditions[right_condition].get(metric) is not None
            }
            contrasts[label][metric] = paired_bootstrap(
                left,
                right,
                args.bootstrap,
                args.seed + contrast_index * 100 + metric_index,
            )

    document = {
        "unit_of_inference": "task",
        "repetition_handling": "mean within task and condition",
        "bootstrap": {
            "method": "paired task resampling with replacement",
            "iterations": args.bootstrap,
            "seed": args.seed,
            "interval": "percentile 95%",
        },
        "metric_direction": {
            "gate_accept": "higher is better",
            "excluded_removed": "higher is better",
            "oracle_correct": "higher is better",
            "wrong_substitute": "lower is better",
        },
        "completed_cells": len(records),
        "ignored_records": ignored,
        "conditions": condition_summary,
        "contrasts": contrasts,
        "task_means": task_means,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary.replace(args.output)

    print(
        "condition              tasks cells gate%  removed% oracle% wrong% "
        "in_tok out_tok sec  fb_ws"
    )
    for condition in CONDITIONS:
        row = condition_summary[condition]
        print(
            f"{condition:<22} "
            f"{row['tasks']:>5} {row['cells']:>5} "
            f"{fmt_rate(row['gate_accept'])} "
            f"{fmt_rate(row['excluded_removed'])} "
            f"{fmt_rate(row['oracle_correct'])} "
            f"{fmt_rate(row['wrong_substitute'])} "
            f"{fmt_number(row['input_tokens'], 0):>6} "
            f"{fmt_number(row['output_tokens'], 0):>7} "
            f"{fmt_number(row['model_duration_sec'], 1):>4} "
            f"{fmt_number(row['feedback_whitespace_tokens'], 0):>6}"
        )

    print()
    print("paired task contrasts, left minus right, percentage points")
    print("contrast                                  metric             estimate [95% CI]")
    for label, metrics in contrasts.items():
        for metric, result in metrics.items():
            estimate = result["estimate"]
            low, high = result["ci95"]
            if estimate is None:
                rendered = "-"
            else:
                rendered = (
                    f"{100 * estimate:6.1f} "
                    f"[{100 * low:6.1f}, {100 * high:6.1f}]"
                )
            print(f"{label:<41} {metric:<18} {rendered}")

    print(f"\njson: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
