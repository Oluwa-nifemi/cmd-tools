#!/usr/bin/env python3
"""Exit 1 when an artifact stops changing, 0 when --max-minutes pass first.

Usage: stall_watch.py <artifact> [--stall-minutes 15] [--max-minutes 120]
"""
import argparse
import os
import sys
import time


def snapshot(path):
    # Size and mtime together: a rewrite to the same size still moves mtime.
    try:
        st = os.stat(path)
        return (st.st_size, st.st_mtime)
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--stall-minutes", type=float, default=15)
    ap.add_argument("--max-minutes", type=float, default=120)
    ap.add_argument("--poll-seconds", type=float, default=30)
    args = ap.parse_args()

    start = last_change = time.time()
    last = snapshot(args.artifact)
    while time.time() - start < args.max_minutes * 60:
        time.sleep(args.poll_seconds)
        now = snapshot(args.artifact)
        if now != last:
            last, last_change = now, time.time()
        elif time.time() - last_change >= args.stall_minutes * 60:
            print(f"STALLED: {args.artifact} unchanged for {args.stall_minutes:g} minutes")
            return 1
    print("OK: max watch time reached without a stall")
    return 0


if __name__ == "__main__":
    sys.exit(main())
