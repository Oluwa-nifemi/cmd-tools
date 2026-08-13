#!/usr/bin/env python3
"""Create and verify presentation artifacts without reading prior outputs."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "deck": ROOT / "template.html",
    "page": ROOT / "page-template.html",
}
REQUIRED = {
    "deck": (
        '<base target="_blank"',
        "window.location.hash",
        "hashchange",
        "@media print",
        "export-btn",
    ),
    "page": (
        '<base target="_blank"',
        'class="toc"',
        '<section class="section"',
        "@media print",
        "export-btn",
    ),
}


def backup_path(output: Path) -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    return output.parent / ".presentation-backups" / (
        f"{output.stem}.{timestamp}{output.suffix}"
    )


def initialize(format_name: str, output: Path) -> None:
    template = TEMPLATES[format_name]
    if not template.is_file():
        raise ValueError(f"Missing template: {template}")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        backup = backup_path(output)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output, backup)
        print(f"Backed up existing artifact: {backup}")

    shutil.copy2(template, output)
    print(f"Created {format_name} artifact: {output}")


def verify(format_name: str, output: Path) -> None:
    if not output.is_file():
        raise ValueError(f"Artifact does not exist: {output}")

    text = output.read_text(encoding="utf-8")
    failures = [token for token in REQUIRED[format_name] if token not in text]
    if "PLACEHOLDER" in text:
        failures.append("no PLACEHOLDER text")

    if failures:
        raise ValueError("Verification failed: " + ", ".join(failures))
    print(f"Verified {format_name} artifact: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize and verify presentation HTML artifacts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "verify"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--format", choices=sorted(TEMPLATES), required=True)
        subparser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            initialize(args.format, args.output)
        else:
            verify(args.format, args.output)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
