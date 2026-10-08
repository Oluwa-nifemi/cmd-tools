#!/usr/bin/env python3
"""Write one readable digest per analysis unit for the analyst sub-agents.

A digest lists every run of the unit: each model call with its time and tokens, what the
model said and which tools it called, a trimmed tool result, and the final answer.
Analysts read digests only; raw/ and compact/ are too big for their context.

Usage: digest.py --audit <audit_dir> [--text-limit 1500] [--result-limit 1200]
Reads:  <audit_dir>/compact/*.json, <audit_dir>/trace_metrics.csv
Writes: <audit_dir>/digest/<unit>.md
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict

CODE_LIMIT = 4000
ANSWER_LIMIT = 3000


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:80] or "unit"


def parse_model_output(text: str, text_limit: int) -> list:
    # PydanticAI exports the model turn as a JSON list of messages whose content is a
    # tool_call, text, or thinking block. Fall back to raw text for other shapes.
    try:
        messages = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return [f"[text] {text[:text_limit]}"]
    if not isinstance(messages, list):
        return [f"[text] {str(messages)[:text_limit]}"]
    lines = []
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else message
        if isinstance(content, str):
            if content.strip():
                lines.append(f"[text] {content[:text_limit]}")
            continue
        if not isinstance(content, dict):
            continue
        kind = content.get("type")
        if kind == "tool_call":
            try:
                arguments = json.loads(content.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {"raw": content.get("arguments")}
            if not isinstance(arguments, dict):
                arguments = {"value": arguments}
            code = arguments.pop("code", None)
            if content.get("name") == "final_result":
                answer = json.dumps(arguments)
                lines.append(f"FINAL RESULT CALL ({len(answer)} chars): {answer[:ANSWER_LIMIT]}")
                continue
            lines.append(f"CALL {content.get('name')} {json.dumps(arguments)[:600]}")
            if code is not None:
                lines.append("~~~")
                lines.append(code[:CODE_LIMIT] + ("\n# ...[code truncated]" if len(code) > CODE_LIMIT else ""))
                lines.append("~~~")
        elif kind in ("text", "thinking"):
            body = content.get("content") or content.get("text") or ""
            if body.strip():
                lines.append(f"[{kind}] {body[:text_limit]}")
    return lines


def render_trace(trace: dict, metrics: dict, text_limit: int, result_limit: int) -> list:
    lines = [
        f"## {trace['group']} run {trace['run'] or '-'} | trace {trace['trace_id']}",
        f"score {trace['score']} | wall {metrics.get('wall_s')} s (minus infra wait {metrics.get('wall_minus_wait_s')} s) | "
        f"model calls {metrics.get('model_calls')} | model time {metrics.get('llm_s')} s | tool time {metrics.get('tool_s')} s | "
        f"peak working tokens {metrics.get('peak_working_tokens')}",
        "",
    ]
    tools_by_turn = defaultdict(list)
    for span in trace["spans"]:
        if span["type"] == "TOOL":
            tools_by_turn[span["turn"]].append(span)
    for span in trace["spans"]:
        if span["type"] != "LLM":
            continue
        lines.append(
            f"### Model call {span['turn'] + 1}: {span['duration_s']} s, in {span['input_tokens']} tok, out {span['output_tokens']} tok"
        )
        lines.extend(parse_model_output(span["output"], text_limit))
        for tool in tools_by_turn.get(span["turn"], []):
            status = "" if tool["status"] in (None, "SUCCESS") else f" STATUS={tool['status']} {tool['error'][:300]}"
            indent = "" if tool["is_top_tool"] else "  (nested) "
            lines.append(f"{indent}RESULT {tool['name']} {tool['duration_s']} s, {tool['output_chars']} chars{status}")
            if tool["is_top_tool"]:
                lines.append(tool["output_head"][:result_limit] + (" ...[truncated]" if tool["output_chars"] > result_limit else ""))
        lines.append("")
    lines.append(f"FINAL ANSWER ({len(trace['final_output'])} chars):")
    lines.append(trace["final_output"][:ANSWER_LIMIT])
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--text-limit", type=int, default=1500)
    parser.add_argument("--result-limit", type=int, default=1200)
    args = parser.parse_args()

    metrics = {}
    with open(os.path.join(args.audit, "trace_metrics.csv")) as handle:
        for row in csv.DictReader(handle):
            metrics[row["trace_id"]] = row
    by_unit = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(args.audit, "compact", "*.json"))):
        with open(path) as handle:
            trace = json.load(handle)
        by_unit[trace["unit"]].append(trace)

    os.makedirs(os.path.join(args.audit, "digest"), exist_ok=True)
    units_index = []
    for unit, traces in sorted(by_unit.items()):
        traces.sort(key=lambda t: (t["group"], t["run"]))
        first = traces[0]
        lines = [f"# Unit {unit}"]
        if first["label"]:
            lines.append(f"Label / question: {first['label']}")
        lines.append("")
        for trace in traces:
            lines.extend(render_trace(trace, metrics.get(trace["trace_id"], {}), args.text_limit, args.result_limit))
        name = safe_name(unit)
        with open(os.path.join(args.audit, "digest", f"{name}.md"), "w") as out:
            out.write("\n".join(lines))
        units_index.append({"unit": unit, "file": f"digest/{name}.md", "traces": len(traces), "label": first["label"]})
    with open(os.path.join(args.audit, "units.json"), "w") as out:
        json.dump(units_index, out, indent=1)
    print(f"wrote {len(units_index)} unit digests to {os.path.join(args.audit, 'digest')}")


if __name__ == "__main__":
    main()

