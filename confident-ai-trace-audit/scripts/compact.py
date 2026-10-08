#!/usr/bin/env python3
"""Turn raw Confident AI traces into compact per-trace JSON files.

Every later script (metrics, digest, patterns, dispatch) reads compact/ only, so the
quirks of the raw export are handled once, here.

Usage: compact.py --audit <audit_dir>
Reads:  <audit_dir>/manifest.csv, <audit_dir>/raw/<trace_id>.json
Writes: <audit_dir>/compact/<trace_id>.json
"""
import argparse
import csv
import json
import os
from datetime import datetime

# Limits keep compact files small enough to grep; raw/ keeps the full text if needed.
LLM_OUTPUT_LIMIT = 20000
TOOL_INPUT_LIMIT = 20000
TOOL_HEAD_LIMIT = 4000
FINAL_OUTPUT_LIMIT = 20000
# Span clocks come from different processes and drift a few ms. A tool span that starts
# just before its LLM span "ends" still belongs to that turn.
TURN_TOLERANCE_S = 0.05


def parse_time(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value)


def code_from_input(value: object) -> str | None:
    # Code tools (e.g. execute_code) take {"code": "..."}. Keep the full code: when the
    # trace has no nested tool spans, the code is the only record of which tools ran.
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if isinstance(value, dict) and isinstance(value.get("code"), str):
        return value["code"]
    return None


def to_number(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_manifest(path: str) -> dict:
    rows = {}
    with open(path) as handle:
        for row in csv.DictReader(handle):
            trace_id = (row.get("trace_id") or "").strip()
            if trace_id:
                rows[trace_id] = row
    return rows


def drop_duplicate_llm_spans(spans: list) -> list:
    # The PydanticAI exporter can log one model request twice: an outer LLM span and a
    # child LLM span with identical token counts (seen on direct-mode ardoq_assistant
    # traces). Keeping both doubles model time and tokens.
    by_uuid = {span["uuid"]: span for span in spans}
    kept = []
    seen = []
    for span in sorted(spans, key=lambda s: s["startTime"]):
        if span["type"] == "LLM":
            parent = by_uuid.get(span.get("parentUuid"))
            if parent is not None and parent["type"] == "LLM":
                continue
            # Fallback for exports where the copy is a sibling instead of a child.
            key = (span.get("inputTokenCount"), span.get("outputTokenCount"))
            start = parse_time(span["startTime"])
            duplicate = False
            if key != (None, None):
                for seen_start, seen_key in seen:
                    if seen_key == key and abs(seen_start - start) < 1.0:
                        duplicate = True
            if duplicate:
                continue
            seen.append((start, key))
        kept.append(span)
    return kept


def nearest_tool_ancestor(span: dict, by_uuid: dict) -> dict | None:
    # Tools called from inside another tool (e.g. data tools inside execute_code) are
    # nested TOOL spans. They cost no model turn of their own.
    parent = by_uuid.get(span.get("parentUuid"))
    while parent is not None:
        if parent["type"] == "TOOL":
            return parent
        parent = by_uuid.get(parent.get("parentUuid"))
    return None


def compact_trace(raw: dict, row: dict) -> dict:
    trace = raw.get("data", raw)
    spans = [s for s in trace.get("spans", []) if s.get("startTime") and s.get("endTime")]
    roots = [s for s in spans if s["type"] == "AGENT" and not s.get("parentUuid")]
    root = roots[0] if roots else None
    start = parse_time(root["startTime"] if root else trace["startTime"])
    end = parse_time(root["endTime"] if root else trace["endTime"])
    final_output = as_text(root.get("output") if root else trace.get("output"))

    all_by_uuid = {s["uuid"]: s for s in spans}
    kept = drop_duplicate_llm_spans([s for s in spans if s["type"] in ("LLM", "TOOL")])

    items = []
    for span in kept:
        span_start = parse_time(span["startTime"])
        span_end = parse_time(span["endTime"])
        item = {
            "uuid": span["uuid"],
            "type": span["type"],
            "name": span["name"],
            "start": span_start,
            "end": span_end,
            "duration_s": round(span_end - span_start, 3),
            "status": span.get("status"),
            "error": as_text(span.get("error"))[:2000],
        }
        if span["type"] == "LLM":
            item["model"] = span.get("model")
            item["input_tokens"] = span.get("inputTokenCount") or 0
            item["output_tokens"] = span.get("outputTokenCount") or 0
            item["output"] = as_text(span.get("output"))[:LLM_OUTPUT_LIMIT]
        else:
            ancestor = nearest_tool_ancestor(span, all_by_uuid)
            output = as_text(span.get("output"))
            item["is_top_tool"] = ancestor is None
            item["top_tool_uuid"] = None if ancestor is None else ancestor["uuid"]
            item["input"] = as_text(span.get("input"))[:TOOL_INPUT_LIMIT]
            item["code"] = code_from_input(span.get("input"))
            item["output_chars"] = len(output)
            item["output_head"] = output[:TOOL_HEAD_LIMIT]
        items.append(item)

    # A turn is one model call plus the top-level tool calls it issued. A top-level tool
    # belongs to the last LLM span that ended before it started; nested tools inherit
    # the turn of their top-level tool.
    llm_items = [i for i in items if i["type"] == "LLM"]
    for index, item in enumerate(llm_items):
        item["turn"] = index
    for item in items:
        if item["type"] != "TOOL" or not item["is_top_tool"]:
            continue
        item["turn"] = -1
        for llm in llm_items:
            if llm["end"] <= item["start"] + TURN_TOLERANCE_S:
                item["turn"] = llm["turn"]
    top_turn = {}
    for item in items:
        if item["type"] == "TOOL" and item["is_top_tool"]:
            top_turn[item["uuid"]] = item["turn"]
    for item in items:
        if item["type"] == "TOOL" and not item["is_top_tool"]:
            item["turn"] = top_turn.get(item["top_tool_uuid"], -1)

    return {
        "trace_id": row["trace_id"].strip(),
        "confident_uuid": trace.get("uuid"),
        "agent_name": trace.get("name"),
        "unit": (row.get("unit") or "").strip() or row["trace_id"].strip(),
        "group": (row.get("group") or "").strip() or "all",
        "run": (row.get("run") or "").strip(),
        "score": to_number(row.get("score")),
        "label": (row.get("label") or "").strip(),
        "start": start,
        "end": end,
        "wall_s": round(end - start, 3),
        "final_output": final_output[:FINAL_OUTPUT_LIMIT],
        "spans": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True, help="audit directory")
    args = parser.parse_args()

    manifest = read_manifest(os.path.join(args.audit, "manifest.csv"))
    os.makedirs(os.path.join(args.audit, "compact"), exist_ok=True)
    written = 0
    missing = []
    for trace_id, row in manifest.items():
        raw_path = os.path.join(args.audit, "raw", f"{trace_id}.json")
        if not os.path.exists(raw_path):
            missing.append(trace_id)
            continue
        with open(raw_path) as handle:
            raw = json.load(handle)
        record = compact_trace(raw, row)
        with open(os.path.join(args.audit, "compact", f"{trace_id}.json"), "w") as out:
            json.dump(record, out, indent=1)
        written += 1
    print(f"compacted {written} traces; missing raw: {len(missing)}")
    for trace_id in missing:
        print("  missing", trace_id)


if __name__ == "__main__":
    main()
