#!/usr/bin/env python3
"""Create, lint, and browser-verify presentation artifacts."""

from __future__ import annotations

import argparse
import html
import json
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
        self.ids: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        attrs_dict = dict(attrs)
        if attrs_dict.get("id"):
            self.ids.append(attrs_dict["id"] or "")
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
        if any(token in text for token in ("<details", "details-toggle", "details-panel")):
            failures.append("deck content must not use details or legacy details panels")
    elif "<details" in text:
        failures.append("page content must not use details; keep content visible")

    duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicate_ids:
        failures.append("unique element IDs; duplicates: " + ", ".join(duplicate_ids))

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


def lint(format_name: str, output: Path) -> None:
    if not output.is_file():
        raise ValueError(f"Artifact does not exist: {output}")

    text = output.read_text(encoding="utf-8")
    parser = ArtifactHTMLParser()
    parser.feed(text)
    parser.close()
    failures = [token for token in REQUIRED[format_name] if token not in text]
    failures.extend(structural_failures(format_name, text))
    if format_name == "page" and "@page { size: A4 landscape;" not in text:
        failures.append("landscape PDF orientation")
    if "PLACEHOLDER" in "\n".join(parser.visible_text):
        failures.append("no PLACEHOLDER text")

    if failures:
        raise ValueError("Lint failed: " + ", ".join(failures))
    print(f"Linted {format_name} artifact: {output}")


def browser_command(agent_browser: str, session: str, *args: str) -> list[str]:
    return [agent_browser, "--session", session, *args]


def run_browser(command: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        command, check=True, text=True, capture_output=capture
    )
    return result.stdout.strip() if capture else ""


def diagnostics_script(format_name: str) -> str:
    root_selector = ".slide.active" if format_name == "deck" else "body"
    vertical_bounds = "r.top < rootRect.top - 1 || r.bottom > rootRect.bottom + 1" if format_name == "deck" else "false"
    root_overflow = "root.scrollWidth > root.clientWidth + 1 || root.scrollHeight > root.clientHeight + 1" if format_name == "deck" else "document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    return f"""(() => {{
      const root = document.querySelector('{root_selector}');
      const rootRect = root.getBoundingClientRect();
      const visible = [...root.querySelectorAll('*')].filter(el => {{
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
      }});
      const selector = el => el.id ? '#' + CSS.escape(el.id) :
        el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].slice(0,2).map(CSS.escape).join('.') : '');
      const clipped = visible.filter(el => {{
        const r = el.getBoundingClientRect();
        return r.left < rootRect.left - 1 || r.right > rootRect.right + 1 || {vertical_bounds};
      }}).map(selector);
      const tinyText = visible.filter(el => {{
        const text = (el.textContent || '').trim();
        if (!text || el.children.length) return false;
        return parseFloat(getComputedStyle(el).fontSize) < 12;
      }}).map(el => ({{selector: selector(el), px: getComputedStyle(el).fontSize}}));
      const svgOverflow = [...root.querySelectorAll('svg')].flatMap(svg => {{
        const box = svg.getBoundingClientRect();
        return [...svg.querySelectorAll('text, foreignObject')].filter(el => {{
          const r = el.getBoundingClientRect();
          return r.left < box.left - 1 || r.right > box.right + 1 ||
            r.top < box.top - 1 || r.bottom > box.bottom + 1;
        }}).map(selector);
      }});
      const containerOverflow = [...root.querySelectorAll('[data-fit-within]')].flatMap(el => {{
        const target = document.querySelector(el.dataset.fitWithin);
        if (!target) return [{{selector: selector(el), target: el.dataset.fitWithin, error: 'missing target'}}];
        const r = el.getBoundingClientRect();
        const box = target.getBoundingClientRect();
        const pad = 4;
        return r.left < box.left + pad || r.right > box.right - pad ||
          r.top < box.top + pad || r.bottom > box.bottom - pad
          ? [{{selector: selector(el), target: el.dataset.fitWithin}}] : [];
      }});
      const unlabeledButtons = [...root.querySelectorAll('button')].filter(el =>
        !(el.textContent || '').trim() && !el.getAttribute('aria-label') && !el.getAttribute('title')
      ).map(selector);
      const wrappedCompactLabels = [...root.querySelectorAll('.pill, .badge, [data-no-wrap]')].flatMap(el => {{
        const range = document.createRange();
        range.selectNodeContents(el);
        const lines = new Set([...range.getClientRects()].map(r => Math.round(r.top)));
        return lines.size > 1 ? [selector(el)] : [];
      }});
      const inlineLabelBody = [...root.querySelectorAll('[data-label-body], .flow-box')].flatMap(el => {{
        const label = el.querySelector('.flow-label, [data-part="label"]');
        const body = el.querySelector('.flow-body, [data-part="body"]');
        if (!label || !body) return [];
        const lr = label.getBoundingClientRect();
        const br = body.getBoundingClientRect();
        return Math.abs(lr.top - br.top) < 4 ? [selector(el)] : [];
      }});
      const fixedChromeIntersections = [...document.querySelectorAll('body *')].filter(el => {{
        const s = getComputedStyle(el);
        return (s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none';
      }}).flatMap(chrome => {{
        const cr = chrome.getBoundingClientRect();
        const hit = [...document.querySelectorAll('main, main section, .section')].some(content => {{
          const r = content.getBoundingClientRect();
          return cr.left < r.right && cr.right > r.left && cr.top < r.bottom && cr.bottom > r.top;
        }});
        return hit ? [selector(chrome)] : [];
      }});
      return JSON.stringify({{
        href: location.href,
        rootOverflow: {root_overflow},
        clipped: [...new Set(clipped)], tinyText, svgOverflow: [...new Set(svgOverflow)],
        containerOverflow, wrappedCompactLabels, inlineLabelBody,
        fixedChromeIntersections, unlabeledButtons
      }});
    }})()"""


def write_contact_sheet(bundle: Path, screenshots: list[Path], report: dict) -> Path:
    cards = "\n".join(
        f'<a class="card" href="{html.escape(path.name)}"><img src="{html.escape(path.name)}"><span>{html.escape(path.stem)}</span></a>'
        for path in screenshots
    )
    contact = bundle / "contact-sheet.html"
    contact.write_text(
        "<!doctype html><meta charset='utf-8'><title>Presentation verification</title>"
        "<style>body{font:16px system-ui;margin:24px;background:#eee;color:#222}"
        "h1{margin:0 0 8px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}"
        ".card{background:white;padding:10px;text-decoration:none;color:inherit;border:1px solid #ccc}"
        "img{width:100%;display:block}.card span{display:block;margin-top:8px;font-weight:600}"
        "pre{background:#111;color:#eee;padding:16px;overflow:auto}</style>"
        f"<h1>Presentation verification</h1><p>{len(screenshots)} rendered states</p>"
        f"<div class='grid'>{cards}</div><h2>Diagnostics</h2><pre>{html.escape(json.dumps(report, indent=2))}</pre>",
        encoding="utf-8",
    )
    return contact


def verify(format_name: str, output: Path) -> None:
    lint(format_name, output)
    agent_browser = shutil.which("agent-browser")
    if agent_browser is None:
        raise ValueError("agent-browser is required for browser verification")

    bundle = output.with_name(f"{output.stem}.verification")
    bundle.mkdir(parents=True, exist_ok=True)
    page_url = output.resolve().as_uri() + "?verify=1"
    session = f"presentation-verify-{output.stem}-{datetime.now().strftime('%H%M%S')}"
    screenshots: list[Path] = []
    diagnostics: list[dict] = []
    failures: list[str] = []

    try:
        run_browser(browser_command(agent_browser, session, "--allow-file-access", "open", page_url))
        if format_name == "deck":
            raw_count = run_browser(browser_command(agent_browser, session, "eval", "document.querySelectorAll('.slide').length"), capture=True)
            slide_count = int(json.loads(raw_count) if raw_count.startswith(('"', '[')) else raw_count)
            for width, height in ((1440, 900), (1263, 863)):
                run_browser(browser_command(agent_browser, session, "set", "viewport", str(width), str(height)))
                for index in range(1, slide_count + 1):
                    run_browser(browser_command(agent_browser, session, "open", f"{page_url}#page-{index}"))
                    path = bundle / f"slide-{index:02d}-{width}x{height}.png"
                    run_browser(browser_command(agent_browser, session, "screenshot", str(path)))
                    screenshots.append(path)
                    raw = run_browser(browser_command(agent_browser, session, "eval", diagnostics_script(format_name)), capture=True)
                    item = json.loads(json.loads(raw) if raw.startswith('\"') else raw)
                    item["slide"] = index
                    item["viewport"] = f"{width}x{height}"
                    diagnostics.append(item)
            run_browser(browser_command(agent_browser, session, "set", "viewport", "1440", "900"))

            run_browser(browser_command(agent_browser, session, "open", f"{page_url}#page-1"))
            run_browser(browser_command(agent_browser, session, "click", "#next-btn"))
            next_hash = run_browser(browser_command(agent_browser, session, "eval", "location.hash"), capture=True)
            if "page-2" not in next_hash and slide_count > 1:
                failures.append("next navigation did not reach slide 2")
            run_browser(browser_command(agent_browser, session, "press", "ArrowLeft"))
            prev_hash = run_browser(browser_command(agent_browser, session, "eval", "location.hash"), capture=True)
            if "page-1" not in prev_hash:
                failures.append("keyboard previous navigation did not reach slide 1")

            declared = run_browser(browser_command(agent_browser, session, "eval", "JSON.stringify([...document.querySelectorAll('[data-verify-target]')].map((el,i)=>{el.setAttribute('data-verify-index',String(i));return {i,target:el.dataset.verifyTarget,slide:[...document.querySelectorAll('.slide')].indexOf(el.closest('.slide'))+1}}))"), capture=True)
            controls = json.loads(json.loads(declared) if declared.startswith('\"') else declared)
            for control in controls:
                selector = f"[data-verify-index='{control['i']}']"
                run_browser(browser_command(agent_browser, session, "open", f"{page_url}#page-{control['slide']}"))
                before = run_browser(browser_command(agent_browser, session, "eval", f"!!document.querySelector({json.dumps(control['target'])}) && getComputedStyle(document.querySelector({json.dumps(control['target'])})).display !== 'none'"), capture=True)
                run_browser(browser_command(agent_browser, session, "click", selector))
                after = run_browser(browser_command(agent_browser, session, "eval", f"!!document.querySelector({json.dumps(control['target'])}) && getComputedStyle(document.querySelector({json.dumps(control['target'])})).display !== 'none'"), capture=True)
                if before == after:
                    failures.append(f"declared control {selector} did not change {control['target']} visibility")
                    continue
                state_path = bundle / f"interaction-{control['i'] + 1:02d}.png"
                run_browser(browser_command(agent_browser, session, "screenshot", str(state_path)))
                screenshots.append(state_path)
                run_browser(browser_command(agent_browser, session, "press", "Escape"))
                closed = run_browser(browser_command(agent_browser, session, "eval", f"getComputedStyle(document.querySelector({json.dumps(control['target'])})).display === 'none'"), capture=True)
                if "true" not in closed.lower():
                    failures.append(f"declared target {control['target']} did not close with Escape")
        else:
            for width, height in ((1440, 1100), (1263, 863)):
                run_browser(browser_command(agent_browser, session, "set", "viewport", str(width), str(height)))
                path = bundle / f"page-full-{width}x{height}.png"
                run_browser(browser_command(agent_browser, session, "screenshot", "--full", str(path)))
                screenshots.append(path)
                raw_count = run_browser(
                    browser_command(agent_browser, session, "eval", "document.querySelectorAll('section.section').length"),
                    capture=True,
                )
                section_count = int(json.loads(raw_count) if raw_count.startswith(('\"', '[')) else raw_count)
                for index in range(section_count):
                    run_browser(
                        browser_command(
                            agent_browser, session, "eval",
                            f"document.querySelectorAll('section.section')[{index}].scrollIntoView({{block:'start'}})",
                        )
                    )
                    annotated = bundle / f"section-{index + 1:02d}-annotated-{width}x{height}.png"
                    run_browser(browser_command(agent_browser, session, "screenshot", "--annotate", str(annotated)))
                    screenshots.append(annotated)
                raw = run_browser(browser_command(agent_browser, session, "eval", diagnostics_script(format_name)), capture=True)
                item = json.loads(json.loads(raw) if raw.startswith('\"') else raw)
                item["viewport"] = f"{width}x{height}"
                diagnostics.append(item)

        errors = run_browser(browser_command(agent_browser, session, "errors"), capture=True)
        if errors and "No page errors" not in errors:
            failures.append("browser page errors: " + errors[:500])
    finally:
        subprocess.run(browser_command(agent_browser, session, "close"), check=False)

    for item in diagnostics:
        label = f"slide {item.get('slide')}" if item.get("slide") else "page"
        for key in ("clipped", "tinyText", "svgOverflow", "containerOverflow",
                    "wrappedCompactLabels", "inlineLabelBody",
                    "fixedChromeIntersections", "unlabeledButtons"):
            if item.get(key):
                failures.append(f"{label}: {key}: {item[key]}")
        if item.get("rootOverflow"):
            failures.append(f"{label}: unexpected root overflow")

    report = {"artifact": str(output), "format": format_name, "diagnostics": diagnostics, "failures": failures}
    (bundle / "diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    contact = write_contact_sheet(bundle, screenshots, report)
    if failures:
        raise ValueError("Browser verification failed:\n- " + "\n- ".join(failures) + f"\nEvidence: {contact}")
    print(f"Browser-verified {format_name} artifact: {output}")
    print(f"Verification bundle: {bundle}")


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
    lint("page", output)
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
    section_dir = output.with_name(f"{output.stem}-section-images")
    section_dir.mkdir(parents=True, exist_ok=True)
    commands = (
        [agent_browser, "--session", session, "--allow-file-access", "open", page_url],
        [agent_browser, "--session", session, "set", "viewport", "1440", "1100", "2"],
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
        raw_count = run_browser(
            browser_command(agent_browser, session, "eval", "document.querySelectorAll('section.section').length"),
            capture=True,
        )
        section_count = int(json.loads(raw_count) if raw_count.startswith(('\"', '[')) else raw_count)
        for index in range(section_count):
            run_browser(
                browser_command(
                    agent_browser, session, "eval",
                    f"document.querySelectorAll('section.section')[{index}].scrollIntoView({{block:'start'}})",
                )
            )
            subprocess.run(
                browser_command(
                    agent_browser, session, "screenshot",
                    str(section_dir / f"section-{index + 1:02d}.png"),
                ),
                check=True,
            )
    finally:
        subprocess.run([agent_browser, "--session", session, "close"], check=False)

    print(f"Exported section PDF: {pdf_output}")
    print(f"Exported long PNG: {png_output}")
    print(f"Exported readable section PNGs: {section_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize and verify presentation HTML artifacts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "lint", "verify", "export"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--format", choices=sorted(TEMPLATES), required=True)
        subparser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            initialize(args.format, args.output)
        elif args.command == "lint":
            lint(args.format, args.output)
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
