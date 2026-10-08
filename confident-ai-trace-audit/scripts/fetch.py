#!/usr/bin/env python3
"""Download full Confident AI traces listed in a manifest.

Usage: fetch.py --audit <audit_dir> [--agent-name NAME] [--since YYYY-MM-DD] [--workers 6]
Reads:  <audit_dir>/manifest.csv (column trace_id required)
Writes: <audit_dir>/raw/<trace_id>.json, <audit_dir>/fetch_report.json

Needs network, so run it with sandbox escalation. Never prints API key values.
Already-downloaded traces are skipped, so it is safe to re-run after a failure.
"""
import argparse
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# EU host. api.eu.confident-ai.com does not resolve; this one does.
HOST = "https://eu.api.confident-ai.com/v1"
# Dev/internal-env traces live behind the dev key, so try it first. A 404 with one key
# can mean "other project", so always try the other key before calling a trace missing.
# CONFIDENT_API_EVAL_KEY is a separate eval project and is deliberately not used.
KEY_NAMES = ["CONFIDENT_API_DEV_KEY", "CONFIDENT_API_KEY"]
MAX_LIST_PAGES = 200


def keys() -> list:
    found = []
    for name in KEY_NAMES:
        value = os.environ.get(name)
        if value:
            found.append((name, value))
    return found


def get_json(url: str, key: str) -> dict:
    # The raw key goes in the CONFIDENT_API_KEY header. Bearer auth returns 401.
    request = urllib.request.Request(url, headers={"CONFIDENT_API_KEY": key})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def fetch_by_uuid(confident_uuid: str) -> tuple:
    last = "no key configured"
    for name, key in keys():
        try:
            return get_json(f"{HOST}/traces/{confident_uuid}", key), name
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code} with {name}"
        except urllib.error.URLError as error:
            last = f"network error: {error.reason}"
    return None, last


def map_ids_by_listing(wanted: set, agent_name: str | None, since: str | None) -> tuple:
    # Ids copied from eval sheets are often OpenTelemetry trace ids, not Confident
    # uuids. Confident stores the OTel id in metadata.trace_id, so page through the
    # project's trace list and join on it.
    mapping = {}
    ambiguous = {}
    for _name, key in keys():
        if wanted <= set(mapping):
            break
        cursor = None
        for _ in range(MAX_LIST_PAGES):
            params = {"pageSize": "100"}
            if cursor:
                params["cursor"] = cursor
            data = get_json(f"{HOST}/traces?" + urllib.parse.urlencode(params), key)["data"]
            oldest = None
            for trace in data.get("traces", []):
                oldest = trace.get("startTime") or oldest
                if agent_name and trace.get("name") != agent_name:
                    continue
                otel_id = (trace.get("metadata") or {}).get("trace_id")
                if otel_id not in wanted:
                    continue
                if otel_id in mapping and mapping[otel_id] != trace["uuid"]:
                    # One OTel trace can hold several agent traces (e.g. sub-agents).
                    # Keep the first and report the rest; pass --agent-name to narrow.
                    ambiguous.setdefault(otel_id, [mapping[otel_id]]).append(trace["uuid"])
                    continue
                mapping[otel_id] = trace["uuid"]
            cursor = data.get("nextCursor")
            if not cursor or wanted <= set(mapping):
                break
            if since and oldest and oldest < since:
                break
    return mapping, ambiguous


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--agent-name", help="only map listed traces with this name, e.g. ardoq_assistant")
    parser.add_argument("--since", help="stop paging once listed traces are older than this ISO date")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    raw_dir = os.path.join(args.audit, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    trace_ids = []
    with open(os.path.join(args.audit, "manifest.csv")) as handle:
        for row in csv.DictReader(handle):
            value = (row.get("trace_id") or "").strip()
            if value:
                trace_ids.append(value)

    report = {"total": len(trace_ids), "cached": [], "by_uuid": [], "mapped": {}, "ambiguous": {}, "missing": {}}
    todo = []
    for trace_id in trace_ids:
        if os.path.exists(os.path.join(raw_dir, f"{trace_id}.json")):
            report["cached"].append(trace_id)
        else:
            todo.append(trace_id)
    if todo and not keys():
        raise SystemExit("Set CONFIDENT_API_DEV_KEY or CONFIDENT_API_KEY first.")

    def save(trace_id: str, payload: dict) -> None:
        with open(os.path.join(raw_dir, f"{trace_id}.json"), "w") as out:
            json.dump(payload, out)

    def try_uuid(pair: tuple) -> tuple:
        trace_id, confident_uuid = pair
        payload, status = fetch_by_uuid(confident_uuid)
        if payload is not None:
            save(trace_id, payload)
        return trace_id, payload is not None, status

    not_found = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for trace_id, ok, status in pool.map(try_uuid, [(t, t) for t in todo]):
            if ok:
                report["by_uuid"].append(trace_id)
            else:
                not_found.append(trace_id)
                report["missing"][trace_id] = status

    if not_found:
        mapping, ambiguous = map_ids_by_listing(set(not_found), args.agent_name, args.since)
        report["ambiguous"] = ambiguous
        pairs = [(t, mapping[t]) for t in not_found if t in mapping]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for trace_id, ok, status in pool.map(try_uuid, pairs):
                if ok:
                    report["mapped"][trace_id] = mapping[trace_id]
                    report["missing"].pop(trace_id, None)
                else:
                    report["missing"][trace_id] = status
        for trace_id in not_found:
            if trace_id not in mapping:
                report["missing"][trace_id] = "not found by uuid or metadata.trace_id"

    with open(os.path.join(args.audit, "fetch_report.json"), "w") as out:
        json.dump(report, out, indent=1)
    print(
        f"total {report['total']} | cached {len(report['cached'])} | by uuid {len(report['by_uuid'])} | "
        f"mapped via metadata.trace_id {len(report['mapped'])} | ambiguous {len(report['ambiguous'])} | "
        f"missing {len(report['missing'])}"
    )
    for trace_id, status in report["missing"].items():
        print("  missing", trace_id, status)


if __name__ == "__main__":
    main()

