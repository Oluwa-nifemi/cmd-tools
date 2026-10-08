"""Count one analyst pattern across every trace. Copy into the audit folder and edit matches().

Usage: python3 count_<pattern>.py --audit <audit_dir>
Prints one line per event, then totals per group: events, traces, units, model seconds.
"""
import argparse
import glob
import json
import os
from collections import defaultdict


def matches(span: dict, trace: dict) -> str | None:
    """Return a short detail string when this span is an event, else None.

    Edit this. span keys: type (LLM or TOOL), name, turn, duration_s, input (TOOL),
    output (LLM), output_head, output_chars, status, error, is_top_tool.
    """
    if span["type"] == "TOOL" and span["name"] == "REPLACE_ME":
        return span["input"][:120]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    totals = defaultdict(lambda: {"events": 0, "traces": set(), "units": set(), "model_s": 0.0})
    for path in sorted(glob.glob(os.path.join(args.audit, "compact", "*.json"))):
        with open(path) as handle:
            trace = json.load(handle)
        model_s_by_turn = {}
        for span in trace["spans"]:
            if span["type"] == "LLM":
                model_s_by_turn[span["turn"]] = span["duration_s"]
        for span in trace["spans"]:
            detail = matches(span, trace)
            if detail is None:
                continue
            # Charge the model time of the turn that wrote the call.
            model_s = model_s_by_turn.get(span["turn"], 0.0)
            print(trace["group"], trace["unit"], f"run {trace['run']}", f"turn {span['turn'] + 1}", f"{model_s} s", detail)
            group = totals[trace["group"]]
            group["events"] += 1
            group["traces"].add(trace["trace_id"])
            group["units"].add(trace["unit"])
            group["model_s"] += model_s

    for name, group in sorted(totals.items()):
        print(f"{name}: events {group['events']} | traces {len(group['traces'])} | units {len(group['units'])} | model s {round(group['model_s'], 1)}")


if __name__ == "__main__":
    main()
