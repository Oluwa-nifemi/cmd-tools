#!/usr/bin/env python3
"""Find candidate traces from a description (time window, agent, org, user) and summarise them.

The person describes the runs ("I ran the eval on org X this morning with agent Y"). The
agent turns that into filters, runs this script, shows the summary, and asks the person
which clusters are relevant. Then it writes manifest.csv from the confirmed rows.

Usage: discover.py --audit <dir> --since 2026-10-05T10:00 [--until 2026-10-05T12:00]
                   [--name ardoq_assistant] [--meta org_label=mcptest --meta model=...]
                   [--user-id ID] [--with-question] [--gap-min 10]
Writes: <dir>/candidates.csv, and raw/<uuid>.json for each trace when --with-question

Times are UTC (Confident stores UTC). Convert the person's local time first.
The list API has no input text, so --with-question downloads each candidate to read its
first user message. Those downloads land in raw/, so fetch.py reuses them.
Needs network: run with sandbox escalation. Never prints API key values.
"""
import argparse
import csv
import json
import os
import urllib.parse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fetch import HOST, fetch_by_uuid, get_json, keys

MAX_PAGES = 500


def parse_time(value: str) -> float:
    if len(value) == 10:
        value += "T00:00"
    if not value.endswith("Z") and "+" not in value[10:]:
        value += "+00:00"
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def first_user_message(payload: dict) -> str:
    trace = payload.get("data", payload)
    value = trace.get("input")
    try:
        messages = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return str(value)[:200]
    if isinstance(messages, list):
        for message in messages:
            if isinstance(message, dict) and str(message.get("role", "")).lower() == "user":
                return str(message.get("content", ""))[:200]
    return str(value or "")[:200]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--since", required=True, help="UTC start, e.g. 2026-10-05T10:00")
    parser.add_argument("--until", help="UTC end; default now")
    parser.add_argument("--name", help="trace name, e.g. ardoq_assistant")
    parser.add_argument("--meta", action="append", default=[], help="metadata key=value, repeatable")
    parser.add_argument("--user-id")
    parser.add_argument("--with-question", action="store_true", help="download each candidate to read its first user message")
    parser.add_argument("--gap-min", type=float, default=10, help="start a new time cluster after this many quiet minutes")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    since = parse_time(args.since)
    until = parse_time(args.until) if args.until else float("inf")
    wanted_meta = dict(item.split("=", 1) for item in args.meta)
    if not keys():
        raise SystemExit("Set CONFIDENT_API_DEV_KEY or CONFIDENT_API_KEY first.")

    rows = []
    for key_name, key in keys():
        cursor = None
        for _ in range(MAX_PAGES):
            params = {"pageSize": "100"}
            if cursor:
                params["cursor"] = cursor
            data = get_json(f"{HOST}/traces?" + urllib.parse.urlencode(params), key)["data"]
            oldest = None
            for trace in data.get("traces", []):
                start = parse_time(trace["startTime"])
                oldest = start if oldest is None else min(oldest, start)
                if not since <= start <= until:
                    continue
                if args.name and trace.get("name") != args.name:
                    continue
                metadata = trace.get("metadata") or {}
                if any(str(metadata.get(k)) != v for k, v in wanted_meta.items()):
                    continue
                if args.user_id and trace.get("userId") != args.user_id:
                    continue
                rows.append({
                    "trace_id": trace["uuid"],
                    "start": trace["startTime"],
                    "latency_s": round((trace.get("latency") or 0) / 1000, 1),
                    "name": trace.get("name"),
                    "status": trace.get("status"),
                    "user_id": trace.get("userId"),
                    "thread_id": trace.get("threadId"),
                    "otel_trace_id": metadata.get("trace_id"),
                    "metadata": json.dumps(metadata, sort_keys=True),
                    "key": key_name,
                    "question": "",
                })
            cursor = data.get("nextCursor")
            if not cursor or (oldest is not None and oldest < since):
                break
        if rows:
            break

    rows.sort(key=lambda row: row["start"])
    if args.with_question and rows:
        raw_dir = os.path.join(args.audit, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        def read_question(row: dict) -> str:
            path = os.path.join(raw_dir, f"{row['trace_id']}.json")
            if os.path.exists(path):
                with open(path) as handle:
                    return first_user_message(json.load(handle))
            payload, _status = fetch_by_uuid(row["trace_id"])
            if payload is None:
                return ""
            with open(path, "w") as out:
                json.dump(payload, out)
            return first_user_message(payload)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for row, question in zip(rows, pool.map(read_question, rows)):
                row["question"] = question

    cluster = 0
    previous = None
    for row in rows:
        start = parse_time(row["start"])
        if previous is not None and start - previous > args.gap_min * 60:
            cluster += 1
        row["cluster"] = cluster
        previous = start

    os.makedirs(args.audit, exist_ok=True)
    fields = ["trace_id", "cluster", "start", "latency_s", "name", "status", "user_id", "thread_id", "otel_trace_id", "question", "metadata", "key"]
    with open(os.path.join(args.audit, "candidates.csv"), "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} candidate traces -> candidates.csv")
    by_cluster = defaultdict(list)
    for row in rows:
        by_cluster[row["cluster"]].append(row)
    for number, members in by_cluster.items():
        names = Counter(row["name"] for row in members)
        questions = Counter(row["question"] for row in members if row["question"])
        print(f"cluster {number}: {len(members)} traces, {members[0]['start'][:19]} to {members[-1]['start'][:19]} UTC")
        print(f"  names: {dict(names)}")
        values = defaultdict(set)
        for row in members:
            for meta_key, meta_value in json.loads(row["metadata"]).items():
                values[meta_key].add(str(meta_value))
        shared = {k: next(iter(v)) for k, v in values.items() if len(v) == 1}
        varying = {k: len(v) for k, v in values.items() if len(v) > 1}
        print(f"  shared metadata: {json.dumps(shared, sort_keys=True)[:300]}")
        print(f"  varying metadata (distinct values): {varying}")
        if questions:
            print(f"  distinct questions: {len(questions)}; top: " + " | ".join(q[:60] for q, _ in questions.most_common(5)))


if __name__ == "__main__":
    main()
