#!/usr/bin/env python3
"""Compute per-trace and per-group metrics from compact traces.

Usage: metrics.py --audit <audit_dir> [--wait-tool NAME --wait-baseline-s 0.4]
Reads:  <audit_dir>/compact/*.json
Writes: <audit_dir>/trace_metrics.csv, <audit_dir>/unit_metrics.csv,
        <audit_dir>/tool_stats.csv, <audit_dir>/summary.json

Medians, not means: a few traces with queueing or retries swing means a lot.
Group summary = median across units of the per-unit median, so every unit counts once
no matter how many runs it has.
"""
import argparse
import csv
import glob
import json
import os
import statistics
from collections import defaultdict


def percentile(values: list, fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def merged_seconds(intervals: list) -> float:
    # Parallel tool calls overlap; sum the union so they are not counted twice.
    total = 0.0
    current_start = None
    current_end = None
    for start, end in sorted(intervals):
        if current_end is None or start > current_end:
            if current_end is not None:
                total += current_end - current_start
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_end is not None:
        total += current_end - current_start
    return total


def trace_metrics(trace: dict, wait_tool: str | None, wait_baseline_s: float) -> dict:
    spans = trace["spans"]
    llm = [s for s in spans if s["type"] == "LLM"]
    top_tools = [s for s in spans if s["type"] == "TOOL" and s["is_top_tool"]]
    nested_tools = [s for s in spans if s["type"] == "TOOL" and not s["is_top_tool"]]
    inputs = [s["input_tokens"] for s in llm]
    outputs = [s["output_tokens"] for s in llm]
    # The first model call's input is mostly system prompt + tool schemas: a fixed prefix
    # every turn re-sends (usually cache-read). Working context = input above that prefix.
    prefix = inputs[0] if inputs else 0
    working = [max(0, value - prefix) for value in inputs]
    llm_s = merged_seconds([(s["start"], s["end"]) for s in llm])
    tool_s = merged_seconds([(s["start"], s["end"]) for s in top_tools])
    errored = [s for s in spans if s["type"] == "TOOL" and s["status"] not in (None, "SUCCESS")]

    row = {
        "trace_id": trace["trace_id"],
        "unit": trace["unit"],
        "group": trace["group"],
        "run": trace["run"],
        "score": trace["score"],
        "wall_s": round(trace["wall_s"], 2),
        "llm_s": round(llm_s, 2),
        "tool_s": round(tool_s, 2),
        "other_s": round(max(0.0, trace["wall_s"] - merged_seconds([(s["start"], s["end"]) for s in llm + top_tools])), 2),
        "model_calls": len(llm),
        "top_tool_calls": len(top_tools),
        "nested_tool_calls": len(nested_tools),
        "errored_tool_spans": len(errored),
        "fixed_prefix_tokens": prefix,
        "total_input_tokens": sum(inputs),
        "total_output_tokens": sum(outputs),
        "total_tokens": sum(inputs) + sum(outputs),
        "peak_input_tokens": max(inputs) if inputs else 0,
        "peak_working_tokens": max(working) if working else 0,
        "total_working_input_tokens": sum(working),
        "final_call_s": round(llm[-1]["duration_s"], 2) if llm else 0,
        "final_call_output_tokens": outputs[-1] if outputs else 0,
        "wait_excess_s": 0.0,
        "wall_minus_wait_s": round(trace["wall_s"], 2),
    }
    if wait_tool:
        # Infra waits (sandbox claim, queue) hide inside one tool's first call. Count the
        # time above a normal call as wait, and report wall time without it.
        calls = [s for s in top_tools if s["name"] == wait_tool]
        if calls:
            excess = max(0.0, calls[0]["duration_s"] - wait_baseline_s)
            row["wait_excess_s"] = round(excess, 2)
            row["wall_minus_wait_s"] = round(trace["wall_s"] - excess, 2)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--wait-tool", help="tool whose first call includes an infrastructure wait (queue, cold start)")
    parser.add_argument("--wait-baseline-s", type=float, default=0.4, help="normal duration of that call without the wait")
    args = parser.parse_args()

    rows = []
    tool_durations = defaultdict(list)
    tool_chars = defaultdict(list)
    tool_errors = defaultdict(int)
    tool_groups = defaultdict(lambda: defaultdict(int))
    for path in sorted(glob.glob(os.path.join(args.audit, "compact", "*.json"))):
        with open(path) as handle:
            trace = json.load(handle)
        rows.append(trace_metrics(trace, args.wait_tool, args.wait_baseline_s))
        for span in trace["spans"]:
            if span["type"] != "TOOL":
                continue
            name = span["name"]
            tool_durations[name].append(span["duration_s"])
            tool_chars[name].append(span["output_chars"])
            tool_groups[name][trace["group"]] += 1
            if span["status"] not in (None, "SUCCESS"):
                tool_errors[name] += 1
    if not rows:
        raise SystemExit("No compact traces found. Run compact.py first.")

    with open(os.path.join(args.audit, "trace_metrics.csv"), "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    groups = sorted({row["group"] for row in rows})
    with open(os.path.join(args.audit, "tool_stats.csv"), "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["tool", "calls", "errors", "median_s", "p90_s", "median_output_chars", "p90_output_chars"] + [f"calls_{g}" for g in groups])
        for name in sorted(tool_durations, key=lambda n: -len(tool_durations[n])):
            writer.writerow([
                name,
                len(tool_durations[name]),
                tool_errors[name],
                round(statistics.median(tool_durations[name]), 2),
                round(percentile(tool_durations[name], 0.9), 2),
                int(statistics.median(tool_chars[name])),
                int(percentile(tool_chars[name], 0.9)),
            ] + [tool_groups[name][g] for g in groups])

    metric_names = [
        "score", "wall_s", "wall_minus_wait_s", "llm_s", "tool_s", "other_s", "model_calls",
        "top_tool_calls", "nested_tool_calls", "errored_tool_spans", "fixed_prefix_tokens",
        "total_tokens", "total_output_tokens", "peak_input_tokens", "peak_working_tokens",
        "final_call_s",
    ]
    summary = {"traces": len(rows), "groups": {}}
    unit_rows_out = []
    for group in groups:
        group_rows = [row for row in rows if row["group"] == group]
        by_unit = defaultdict(list)
        for row in group_rows:
            by_unit[row["unit"]].append(row)
        stats = {"traces": len(group_rows), "units": len(by_unit)}
        for unit, unit_rows in sorted(by_unit.items()):
            unit_row = {"unit": unit, "group": group, "runs": len(unit_rows)}
            for metric in metric_names:
                values = [float(r[metric]) for r in unit_rows if r[metric] is not None]
                unit_row[metric] = round(statistics.median(values), 2) if values else None
            unit_rows_out.append(unit_row)
        for metric in metric_names:
            unit_medians = []
            for unit_rows in by_unit.values():
                values = [float(r[metric]) for r in unit_rows if r[metric] is not None]
                if values:
                    unit_medians.append(statistics.median(values))
            if unit_medians:
                stats[metric] = {
                    "median_of_unit_medians": round(statistics.median(unit_medians), 2),
                    "p90_of_unit_medians": round(percentile(unit_medians, 0.9), 2),
                    "mean_of_unit_medians": round(statistics.mean(unit_medians), 3),
                }
        summary["groups"][group] = stats
    units_per_group = defaultdict(set)
    for row in unit_rows_out:
        units_per_group[row["group"]].add(row["unit"])
    all_units = set().union(*units_per_group.values())
    summary["units_not_in_every_group"] = sorted(u for u in all_units if any(u not in s for s in units_per_group.values()))
    with open(os.path.join(args.audit, "summary.json"), "w") as out:
        json.dump(summary, out, indent=1)
    with open(os.path.join(args.audit, "unit_metrics.csv"), "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(unit_rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(unit_rows_out)

    print(f"{len(rows)} traces, groups: {', '.join(groups)}")
    if summary["units_not_in_every_group"]:
        print("WARNING units missing from some group (exclude before comparing): " + ", ".join(summary["units_not_in_every_group"]))
    for group, stats in summary["groups"].items():
        def median_of(metric: str) -> str:
            value = stats.get(metric, {}).get("median_of_unit_medians")
            return "n/a" if value is None else str(value)
        print(
            f"  {group}: units {stats['units']} | score {median_of('score')} | wall {median_of('wall_s')} s | "
            f"wall-wait {median_of('wall_minus_wait_s')} s | model {median_of('llm_s')} s | "
            f"calls {median_of('model_calls')} | total tok {median_of('total_tokens')} | "
            f"peak working tok {median_of('peak_working_tokens')}"
        )
    print("per-unit median wall s (wall minus wait):")
    for row in unit_rows_out:
        print(f"  {row['unit']} {row['group']}: {row['wall_s']} ({row['wall_minus_wait_s']}) over {row['runs']} runs")


if __name__ == "__main__":
    main()
