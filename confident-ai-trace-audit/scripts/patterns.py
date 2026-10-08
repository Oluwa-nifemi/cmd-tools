#!/usr/bin/env python3
"""Count generic waste patterns across every compact trace.

Analysts find patterns in a few units; this script counts them in all traces. A pattern
without a count from here (or from a custom script) is still a hypothesis.

Usage: patterns.py --audit <audit_dir> [--presentation-tools get_asset_link,build_chart]
                   [--big-output-chars 8000]
Reads:  <audit_dir>/compact/*.json
Writes: <audit_dir>/patterns.json, <audit_dir>/pattern_events.csv

Built-in patterns, all per group:
- errored_tool_calls: tool spans with a non-success status, grouped by tool + error head.
- retry_after_error: a turn that errored and the next turn calls the same tool again.
- repeated_identical_calls: same tool with the same input twice in one trace.
- big_tool_outputs: tool outputs above --big-output-chars (context bloat).
- single_tool_turns_in_a_row: consecutive turns that each call exactly one top-level tool.
  These are candidates for batching; the analysts decide whether they were dependent.
- presentation_only_turns: turns whose tools (top-level and nested) are all in
  --presentation-tools. Skipped when the list is empty.
- tail_turns: non-final turns after the last turn that called a non-presentation tool.
- no_tool_turns: non-final model calls that call no tool at all.
- no_call_cells: code-tool calls whose code calls no tool function (e.g. only print("done")).
- slow_model_calls: model calls above the group's p90 duration.

Code tools: when a tool span has code (e.g. execute_code) and no nested tool spans, the
tools it ran are read from the code: every bare function call that is not a Python
builtin and not defined in the code. Method calls (x.y()) are ignored.
"""
import argparse
import ast
import builtins
import csv
import glob
import json
import os
import re
import statistics
from collections import Counter, defaultdict

PYTHON_NAMES = set(dir(builtins))
# Fallback for code that does not parse (e.g. truncated input). Can match comments.
CALL_PATTERN = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\(")


def functions_called(code: str) -> set:
    # Parse instead of regex so tool names inside comments or strings do not count.
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {name for name in CALL_PATTERN.findall(code) if name not in PYTHON_NAMES}
    defined = set()
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)
    return called - defined - PYTHON_NAMES


def turn_tool_names(spans: list) -> set:
    nested_parents = {s["top_tool_uuid"] for s in spans if not s["is_top_tool"]}
    names = set()
    for span in spans:
        if span.get("code") is not None and span["uuid"] not in nested_parents:
            names |= functions_called(span["code"])
        elif span.get("code") is None:
            names.add(span["name"])
    return names


def percentile(values: list, fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--presentation-tools", default="", help="comma list of tools that only format or link")
    parser.add_argument("--big-output-chars", type=int, default=8000)
    args = parser.parse_args()
    presentation = {name.strip() for name in args.presentation_tools.split(",") if name.strip()}

    traces = []
    for path in sorted(glob.glob(os.path.join(args.audit, "compact", "*.json"))):
        with open(path) as handle:
            traces.append(json.load(handle))
    if not traces:
        raise SystemExit("No compact traces found. Run compact.py first.")

    llm_durations = defaultdict(list)
    for trace in traces:
        for span in trace["spans"]:
            if span["type"] == "LLM":
                llm_durations[trace["group"]].append(span["duration_s"])
    slow_cutoff = {group: percentile(values, 0.9) for group, values in llm_durations.items()}

    events = []

    def add(trace: dict, pattern: str, turn: int, seconds: float, detail: str) -> None:
        events.append({
            "group": trace["group"], "unit": trace["unit"], "run": trace["run"], "trace_id": trace["trace_id"],
            "pattern": pattern, "turn": turn + 1, "model_s": round(seconds, 2), "detail": detail[:200],
        })

    error_kinds = Counter()
    for trace in traces:
        llm = {s["turn"]: s for s in trace["spans"] if s["type"] == "LLM"}
        last_turn = max(llm) if llm else -1
        tools_by_turn = defaultdict(list)
        for span in trace["spans"]:
            if span["type"] == "TOOL":
                tools_by_turn[span["turn"]].append(span)

        # Model time is charged to the turn that wrote the call: that is the cost the
        # model paid to produce it, and what a merged or skipped turn would save.
        def turn_seconds(turn: int) -> float:
            return llm[turn]["duration_s"] if turn in llm else 0.0

        for turn, spans in tools_by_turn.items():
            for span in spans:
                if span["status"] not in (None, "SUCCESS"):
                    head = (span["error"] or span["output_head"] or "").replace("\n", " ")[:80]
                    error_kinds[(trace["group"], span["name"], head)] += 1
                    add(trace, "errored_tool_calls", turn, turn_seconds(turn), f"{span['name']}: {head}")
                    next_names = {s["name"] for s in tools_by_turn.get(turn + 1, [])}
                    if span["name"] in next_names or (span["is_top_tool"] is False and next_names):
                        add(trace, "retry_after_error", turn + 1, turn_seconds(turn + 1), span["name"])
                if span["output_chars"] > args.big_output_chars:
                    add(trace, "big_tool_outputs", turn, 0.0, f"{span['name']} {span['output_chars']} chars")

        seen_calls = Counter()
        for span in trace["spans"]:
            if span["type"] == "TOOL" and span["is_top_tool"]:
                seen_calls[(span["name"], span["input"])] += 1
        for (name, _), count in seen_calls.items():
            if count > 1:
                add(trace, "repeated_identical_calls", -1, 0.0, f"{name} x{count}")

        previous_single = False
        last_working_turn = -1
        for turn in sorted(llm):
            top = [s for s in tools_by_turn.get(turn, []) if s["is_top_tool"]]
            names = turn_tool_names(tools_by_turn.get(turn, []))
            nested_parents = {s["top_tool_uuid"] for s in tools_by_turn.get(turn, []) if not s["is_top_tool"]}
            for span in top:
                if span.get("code") is None or span["uuid"] in nested_parents:
                    continue
                if not functions_called(span["code"]):
                    add(trace, "no_call_cells", turn, turn_seconds(turn), span["code"].strip().replace("\n", " / ")[-120:])
            single = len(top) == 1
            if single and previous_single:
                add(trace, "single_tool_turns_in_a_row", turn, turn_seconds(turn), top[0]["name"])
            previous_single = single
            if not top and turn != last_turn:
                add(trace, "no_tool_turns", turn, turn_seconds(turn), "")
            if names and presentation and names <= presentation:
                add(trace, "presentation_only_turns", turn, turn_seconds(turn), ",".join(sorted(names)))
            if names and not names <= presentation:
                last_working_turn = turn
            if llm[turn]["duration_s"] > slow_cutoff.get(trace["group"], 1e9):
                add(trace, "slow_model_calls", turn, llm[turn]["duration_s"], f"out {llm[turn]['output_tokens']} tok")
        for turn in sorted(llm):
            if last_working_turn < turn < last_turn:
                add(trace, "tail_turns", turn, turn_seconds(turn), ",".join(sorted(turn_tool_names(tools_by_turn.get(turn, [])))) or "(no tool call)")

    traces_per_group = Counter(trace["group"] for trace in traces)
    summary = defaultdict(dict)
    by_key = defaultdict(list)
    for event in events:
        by_key[(event["group"], event["pattern"])].append(event)
    for (group, pattern), group_events in sorted(by_key.items()):
        summary[group][pattern] = {
            "events": len(group_events),
            "traces": len({e["trace_id"] for e in group_events}),
            "traces_in_group": traces_per_group[group],
            "units": len({e["unit"] for e in group_events}),
            "model_s_total": round(sum(e["model_s"] for e in group_events), 1),
            "model_s_median": round(statistics.median([e["model_s"] for e in group_events]), 2),
        }
    top_errors = [
        {"group": group, "tool": tool, "error_head": head, "count": count}
        for (group, tool, head), count in error_kinds.most_common(30)
    ]
    with open(os.path.join(args.audit, "patterns.json"), "w") as out:
        json.dump({"patterns": summary, "top_errors": top_errors, "presentation_tools": sorted(presentation)}, out, indent=1)
    with open(os.path.join(args.audit, "pattern_events.csv"), "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["group", "unit", "run", "trace_id", "pattern", "turn", "model_s", "detail"])
        writer.writeheader()
        writer.writerows(events)

    for group, patterns in summary.items():
        print(f"{group} ({traces_per_group[group]} traces)")
        for pattern, stats in patterns.items():
            print(
                f"  {pattern:28s} events {stats['events']:5d} | traces {stats['traces']:4d} | "
                f"model s total {stats['model_s_total']:8.1f} | median {stats['model_s_median']}"
            )
    if top_errors:
        print("top errors:")
        for item in top_errors[:10]:
            print(f"  {item['group']} {item['tool']} x{item['count']}: {item['error_head']}")


if __name__ == "__main__":
    main()
