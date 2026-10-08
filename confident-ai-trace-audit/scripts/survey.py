#!/usr/bin/env python3
"""Describe the tools seen in compact traces so the agent can write profile.py.

Usage: survey.py --audit <audit_dir>
Reads:  <audit_dir>/compact/*.json
Writes: <audit_dir>/survey.json

Per tool it prints what the agent needs to decide the profile and flags on its own:
- calls per group, and the share of calls with nested tool spans
- input keys, and keys holding long text (a "code" or "query" key hints that the tool
  runs other tools or code without logging them)
- first-call vs later-call median duration (a large gap hints at an infra wait;
  use the tool for metrics.py --wait-tool)
- position: share of calls in the last tool turn of a trace (high share plus small
  outputs hints at a presentation tool)
"""
import argparse
import glob
import json
import os
import statistics
from collections import defaultdict

LONG_TEXT_CHARS = 200


def input_keys(text: str) -> tuple:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return (), ()
    if not isinstance(value, dict):
        return (), ()
    long_keys = [key for key, item in value.items() if isinstance(item, str) and len(item) > LONG_TEXT_CHARS]
    return tuple(sorted(value)), tuple(sorted(long_keys))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    stats = defaultdict(lambda: {
        "calls": defaultdict(int), "with_nested": 0, "keys": defaultdict(int), "long_keys": defaultdict(int),
        "first_s": [], "later_s": [], "last_tool_turn": 0, "output_chars": [], "sample_input": "",
    })
    traces = 0
    for path in sorted(glob.glob(os.path.join(args.audit, "compact", "*.json"))):
        with open(path) as handle:
            trace = json.load(handle)
        traces += 1
        top = [s for s in trace["spans"] if s["type"] == "TOOL" and s["is_top_tool"]]
        parents = {s["top_tool_uuid"] for s in trace["spans"] if s["type"] == "TOOL" and not s["is_top_tool"]}
        last_turn = max((s["turn"] for s in top), default=None)
        seen = set()
        for span in top:
            item = stats[span["name"]]
            item["calls"][trace["group"]] += 1
            if span["uuid"] in parents:
                item["with_nested"] += 1
            keys, long_keys = input_keys(span["input"])
            for key in keys:
                item["keys"][key] += 1
            for key in long_keys:
                item["long_keys"][key] += 1
            if span["name"] in seen:
                item["later_s"].append(span["duration_s"])
            else:
                item["first_s"].append(span["duration_s"])
                seen.add(span["name"])
            if span["turn"] == last_turn:
                item["last_tool_turn"] += 1
            item["output_chars"].append(span["output_chars"])
            if not item["sample_input"]:
                item["sample_input"] = span["input"][:300]

    report = {"traces": traces, "tools": {}}
    for name, item in sorted(stats.items(), key=lambda pair: -sum(pair[1]["calls"].values())):
        total = sum(item["calls"].values())
        first = round(statistics.median(item["first_s"]), 2) if item["first_s"] else None
        later = round(statistics.median(item["later_s"]), 2) if item["later_s"] else None
        report["tools"][name] = {
            "calls_by_group": dict(item["calls"]),
            "share_with_nested_spans": round(item["with_nested"] / total, 2),
            "input_keys": sorted(item["keys"]),
            "long_text_keys": sorted(item["long_keys"]),
            "first_call_median_s": first,
            "later_call_median_s": later,
            "share_in_last_tool_turn": round(item["last_tool_turn"] / total, 2),
            "median_output_chars": int(statistics.median(item["output_chars"])),
            "sample_input": item["sample_input"],
        }
    with open(os.path.join(args.audit, "survey.json"), "w") as out:
        json.dump(report, out, indent=1)

    print(f"{traces} traces, {len(report['tools'])} tools (details in survey.json)")
    for name, tool in report["tools"].items():
        hints = []
        if tool["long_text_keys"] and tool["share_with_nested_spans"] < 0.5:
            hints.append(f"long input {tool['long_text_keys']} and few nested spans: may run tools unlogged")
        first, later = tool["first_call_median_s"], tool["later_call_median_s"]
        if first is not None and later is not None and first > 3 * max(later, 0.1) and first - later > 2:
            hints.append(f"first call {first} s vs later {later} s: possible infra wait")
        if tool["share_in_last_tool_turn"] >= 0.6 and tool["median_output_chars"] < 2000:
            hints.append("mostly in the last tool turn with small output: possible presentation tool")
        print(f"  {name}: calls {tool['calls_by_group']} | out {tool['median_output_chars']} chars | " + ("; ".join(hints) or "no hints"))


if __name__ == "__main__":
    main()
