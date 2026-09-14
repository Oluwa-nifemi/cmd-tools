#!/usr/bin/env python3
"""Create and verify presentation artifacts without reading prior outputs."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from html.parser import HTMLParser
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
        'id="section-pdf-link"',
        'id="long-png-link"',
        "break-before: page",
    ),
}
TEMPLATE_INSTRUCTION_TEXT = (
    "PRESENTATION TEMPLATE",
    "HOW TO USE:",
    "replace everything between START and END",
    "Example slide — delete me",
)


class ArtifactHTMLParser(HTMLParser):
    """Collect browser-visible text and document structure from an artifact."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tag_counts: dict[str, int] = {}
        self.visible_text: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        if tag in {"script", "style"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            stripped = data.strip()
            if stripped:
                self.visible_text.append(stripped)


def structural_failures(format_name: str, text: str) -> list[str]:
    parser = ArtifactHTMLParser()
    parser.feed(text)
    parser.close()

    failures = []
    for tag in ("html", "head", "body"):
        count = parser.tag_counts.get(tag, 0)
        if count != 1:
            failures.append(f"exactly one <{tag}> element, found {count}")

    visible_text = "\n".join(parser.visible_text)
    leaked = [token for token in TEMPLATE_INSTRUCTION_TEXT if token in visible_text]
    if leaked:
        failures.append("no browser-visible template instructions")

    if format_name == "deck":
        slide_count = text.count('<section class="slide')
        cover_count = text.count('<section class="slide cover"')
        if slide_count < 1:
            failures.append("at least one deck slide")
        if cover_count != 1:
            failures.append(f"exactly one cover slide, found {cover_count}")

    return failures


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
    failures.extend(structural_failures(format_name, text))
    if format_name == "page" and "@page { size: A4 landscape;" not in text:
        failures.append("landscape PDF orientation")
    if "PLACEHOLDER" in text:
        failures.append("no PLACEHOLDER text")

    if failures:
        raise ValueError("Verification failed: " + ", ".join(failures))
    print(f"Verified {format_name} artifact: {output}")


def chrome_executable() -> str:
    """Find Chrome for PDF export; its CLI honors the template's CSS page size."""
    candidates = (
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise ValueError("Chrome or Chromium is required for page PDF export")


def page_export_paths(output: Path) -> tuple[Path, Path]:
    return (
        output.with_name(f"{output.stem}-sections.pdf"),
        output.with_name(f"{output.stem}-long.png"),
    )


def export_page(output: Path) -> None:
    verify("page", output)
    agent_browser = shutil.which("agent-browser")
    if agent_browser is None:
        raise ValueError("agent-browser is required for full-height PNG export")

    pdf_output, png_output = page_export_paths(output)
    page_url = output.resolve().as_uri()

    # agent-browser's PDF command currently defaults to US Letter. Chrome's
    # native print path honors the template's @page A4 landscape declaration.
    subprocess.run(
        [
            chrome_executable(),
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_output}",
            page_url,
        ],
        check=True,
    )

    session = f"presentation-export-{output.stem}"
    commands = (
        [agent_browser, "--session", session, "--allow-file-access", "open", page_url],
        [agent_browser, "--session", session, "set", "viewport", "1440", "1100"],
        [
            agent_browser,
            "--session",
            session,
            "eval",
            "document.getElementById('page-comment-controls').style.display='none'",
        ],
        [agent_browser, "--session", session, "screenshot", "--full", str(png_output)],
    )
    try:
        for command in commands:
            subprocess.run(command, check=True)
    finally:
        subprocess.run([agent_browser, "--session", session, "close"], check=False)

    print(f"Exported section PDF: {pdf_output}")
    print(f"Exported long PNG: {png_output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize and verify presentation HTML artifacts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "verify", "export"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--format", choices=sorted(TEMPLATES), required=True)
        subparser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            initialize(args.format, args.output)
        elif args.command == "verify":
            verify(args.format, args.output)
        elif args.format != "page":
            raise ValueError("Export currently supports only page format")
        else:
            export_page(args.output)
    except (ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
