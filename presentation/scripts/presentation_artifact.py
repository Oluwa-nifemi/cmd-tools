#!/usr/bin/env python3
"""Create, lint, and browser-verify presentation artifacts."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "deck": ROOT / "template.html",
    "page": ROOT / "page-template.html",
    "interactive": ROOT / "interactive-template.html",
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
    "interactive": (
        '<base target="_blank"',
        'id="stage"',
        'id="story"',
        'id="honesty"',
        'data-depth="overview"',
        'id="explore-btn"',
        "window.Stage",
    ),
}
TEMPLATE_INSTRUCTION_TEXT = (
    "INTERACTIVE TEMPLATE",
    "PRESENTATION TEMPLATE",
    "HOW TO USE:",
    "replace everything between START and END",
    "Example slide — delete me",
    "Example chapter — delete me",
)
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}


class ArtifactHTMLParser(HTMLParser):
    """Collect browser-visible text and document structure from an artifact."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tag_counts: dict[str, int] = {}
        self.visible_text: list[str] = []
        self.ids: list[str] = []
        self.verify_controls = 0
        self._hidden_depth = 0
        self.chapters: list[dict] = []
        self.stray_details = 0
        self._chapter_depth = 0
        self._claim_depth = 0
        self._open: list[str] = []
        self.nodes: list[dict] = []
        self.openers: list[str] = []
        self._node_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        attrs_dict = dict(attrs)
        if "data-verify-target" in attrs_dict:
            self.verify_controls += 1
        if attrs_dict.get("id"):
            self.ids.append(attrs_dict["id"] or "")
        if tag in {"script", "style"}:
            self._hidden_depth += 1
        classes = (attrs_dict.get("class") or "").split()
        if attrs_dict.get("data-open-node"):
            self.openers.append(attrs_dict["data-open-node"] or "")
        if tag in VOID_TAGS:
            return
        self._open.append(tag)
        if tag == "article" and "chapter" in classes:
            self.chapters.append({"claim": ""})
            self._chapter_depth = len(self._open)
        elif tag == "article" and "node" in classes:
            self.nodes.append({"id": attrs_dict.get("data-node") or "", "parent": attrs_dict.get("data-parent"), "claim": ""})
            self._node_depth = len(self._open)
        elif (self._chapter_depth or self._node_depth) and "claim" in classes and not self._claim_depth:
            self._claim_depth = len(self._open)
        if tag == "details" and "deeper" not in classes:
            self.stray_details += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._hidden_depth:
            self._hidden_depth -= 1
        if tag in VOID_TAGS or tag not in self._open:
            return
        while self._open:
            depth = len(self._open)
            closed = self._open.pop()
            if depth == self._claim_depth:
                self._claim_depth = 0
            if depth == self._chapter_depth:
                self._chapter_depth = 0
            if depth == self._node_depth:
                self._node_depth = 0
            if closed == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            stripped = data.strip()
            if stripped:
                self.visible_text.append(stripped)
                if self._claim_depth and self._node_depth and self.nodes:
                    self.nodes[-1]["claim"] += stripped
                elif self._claim_depth and self.chapters:
                    self.chapters[-1]["claim"] += stripped


def node_failures(nodes: list[dict], openers: list[str]) -> list[str]:
    if not nodes:
        return []
    failures = []
    ids = [node["id"] for node in nodes]
    for node_id in ids:
        if not re.fullmatch(r"[a-z0-9-]+", node_id):
            failures.append(f"node id {node_id or '(empty)'} must use lowercase letters, digits, and hyphens")
    for node_id in sorted({i for i in ids if ids.count(i) > 1}):
        failures.append(f"duplicate node id {node_id}")
    known = set(ids)
    roots = [node["id"] for node in nodes if not node["parent"]]
    if len(roots) != 1:
        failures.append(f"exactly one root node (no data-parent), found {len(roots)}")
    children: dict[str, list[str]] = {}
    for node in nodes:
        if node["parent"]:
            if node["parent"] not in known:
                failures.append(f"node {node['id']} has unknown parent {node['parent']}")
            children.setdefault(node["parent"], []).append(node["id"])
        if not node["claim"]:
            failures.append(f"node {node['id']} needs a visible claim")
    reached: set[str] = set()
    pending = list(roots[:1])
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(children.get(current, []))
    for node in nodes:
        if node["id"] not in reached and node["parent"] in known:
            failures.append(f"node {node['id']} is not reachable from the root")
    for target in sorted(set(openers) - known):
        failures.append(f"data-open-node points to unknown node {target}")
    return failures


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
    elif format_name == "interactive":
        if not parser.chapters:
            failures.append("at least one chapter")
        for index, chapter in enumerate(parser.chapters, start=1):
            if not chapter["claim"]:
                failures.append(f"chapter {index} needs a visible claim")
        if parser.stray_details:
            failures.append("interactive content may use details only for Go deeper (class=deeper)")
        failures.extend(node_failures(parser.nodes, parser.openers))
        if parser.openers and not parser.nodes:
            failures.append("data-open-node used but no drill-down nodes exist")
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
    # Launch flags must stay identical: changing file access can relaunch Chrome.
    verifying = session.startswith("presentation-verify-")
    name = session.removeprefix("presentation-verify-") if verifying else session
    # Disabling QUIC reduced CDN load time in local probes; resources stay unchanged.
    flags = ["--namespace", name, "--pin-tab", "--no-webmcp", "--headed", "false",
             "--args", "--disable-quic"] if verifying else []
    return [agent_browser, "--session", name, *flags, "--allow-file-access", *args]


def run_browser(command: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        command, check=True, text=True, capture_output=True, timeout=60,
        env={**os.environ, "AGENT_BROWSER_DEFAULT_TIMEOUT": "5000"},
    )
    return result.stdout.strip() if capture else ""


def parse_eval(raw: str):
    value = json.loads(raw) if raw else None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def control_failures(label: str, before: dict, after: dict, declared: list[str]) -> list[str]:
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    if not changed:
        return [f"{label} did not change the stage"]
    undeclared = [key for key in changed if key not in declared]
    if undeclared:
        return [f"{label} changed undeclared stage keys: " + ", ".join(undeclared)]
    return []


def verify_interactive(agent_browser: str, session: str, page_url: str, bundle: Path,
                       screenshots: list[Path], diagnostics: list[dict], failures: list[str]) -> None:
    def browse(*args: str) -> None:
        run_browser(browser_command(agent_browser, session, *args))

    def evaluate(script: str):
        return parse_eval(run_browser(browser_command(agent_browser, session, "eval", script), capture=True))

    def enter_chapter(index: int) -> None:
        browse("eval", f"document.querySelectorAll('article.chapter')[{index}].scrollIntoView({{block:'start'}})")
        browse("wait", "700")

    chapter_count = int(evaluate("document.querySelectorAll('article.chapter').length"))
    for width, height in ((1440, 900), (1263, 863)):
        browse("set", "viewport", str(width), str(height))
        browse("open", page_url)
        browse("wait", "500")
        for index in range(chapter_count):
            enter_chapter(index)
            path = bundle / f"chapter-{index + 1:02d}-{width}x{height}.png"
            browse("screenshot", str(path))
            screenshots.append(path)
            item = evaluate(diagnostics_script("interactive"))
            item["chapter"] = index + 1
            item["viewport"] = f"{width}x{height}"
            diagnostics.append(item)
            synced = evaluate(
                f"window.Stage.state().view === document.querySelectorAll('article.chapter')[{index}].dataset.view"
            )
            if synced is not True:
                failures.append(f"chapter {index + 1} at {width}x{height} did not set the stage view")

    tag_controls = (
        "JSON.stringify([...document.querySelectorAll('[data-stage-control]')].map((el, i) => {"
        "el.setAttribute('data-control-index', String(i));"
        "return {i, chapter: [...document.querySelectorAll('article.chapter')].indexOf(el.closest('article.chapter')),"
        "changes: (el.dataset.changes || '').split(',').map(s => s.trim()).filter(Boolean)};}))"
    )

    def fresh_page() -> None:
        browse("open", page_url)
        browse("wait", "500")

    browse("set", "viewport", "1440", "900")
    fresh_page()
    controls = evaluate(tag_controls)
    for control in controls:
        label = f"control {control['i'] + 1} (chapter {control['chapter'] + 1})"
        if control["chapter"] < 0:
            failures.append(f"control {control['i'] + 1} is outside any chapter")
            continue
        if not control["changes"]:
            failures.append(f"{label} must declare data-changes")
        fresh_page()
        evaluate(tag_controls)
        enter_chapter(control["chapter"])
        evaluate(
            f"(() => {{ const el = document.querySelector(\"[data-control-index='{control['i']}']\");"
            "const group = el.closest('[data-control-group]');"
            "if (!group || el.getAttribute('aria-pressed') !== 'true') return false;"
            "const other = [...group.querySelectorAll('[data-stage-control]')].find(b => b !== el);"
            "if (other) other.click(); return !!other; })()"
        )
        browse("wait", "300")
        before = evaluate("JSON.stringify(window.Stage.state())")
        browse("click", f"[data-control-index='{control['i']}']")
        browse("wait", "500")
        after = evaluate("JSON.stringify(window.Stage.state())")
        failures.extend(control_failures(label, before, after, control["changes"]))
        path = bundle / f"control-{control['i'] + 1:02d}.png"
        browse("screenshot", str(path))
        screenshots.append(path)

    fresh_page()
    enter_chapter(0)
    browse("click", "[data-depth='overview']")
    browse("wait", "300")
    overview = evaluate(
        "JSON.stringify({claims: [...document.querySelectorAll('.chapter .claim')].every(el => el.offsetParent !== null),"
        "full: [...document.querySelectorAll('.chapter .full')].some(el => el.offsetParent !== null)})"
    )
    if not overview["claims"]:
        failures.append("overview mode hides a chapter claim")
    if overview["full"]:
        failures.append("overview mode still shows full-depth content")
    path = bundle / "overview.png"
    browse("screenshot", str(path))
    screenshots.append(path)
    browse("click", "[data-depth='full']")

    browse("click", "#explore-btn")
    browse("wait", "500")
    if evaluate("document.body.classList.contains('explore')") is not True:
        failures.append("explore button did not enter explore mode")
    path = bundle / "explore.png"
    browse("screenshot", str(path))
    screenshots.append(path)
    browse("click", "#explore-btn")

    nodes = evaluate(
        "JSON.stringify([...document.querySelectorAll('article.node')].map(n => ({id: n.dataset.node, view: n.dataset.view || '',"
        "children: [...document.querySelectorAll('article.node')].filter(c => c.dataset.parent === n.dataset.node).length})))"
    )
    if nodes:
        verify_drilldown(browse, evaluate, page_url, nodes, bundle, screenshots, diagnostics, failures)


def verify_drilldown(browse, evaluate, page_url: str, nodes: list[dict], bundle: Path,
                     screenshots: list[Path], diagnostics: list[dict], failures: list[str]) -> None:
    for node in nodes:
        browse("open", f"{page_url}#node={node['id']}")
        browse("wait", "500")
        result = evaluate(
            "JSON.stringify({drill: document.body.classList.contains('drill'),"
            f"open: !!document.querySelector(\"article.node.open[data-node='{node['id']}']\"),"
            "state: window.Stage.state(),"
            "children: document.querySelectorAll('#children [data-open-node]').length,"
            "crumbs: document.querySelectorAll('#crumbs button').length})"
        )
        label = f"node {node['id']}"
        if not result["drill"] or not result["open"]:
            failures.append(f"{label} did not open from #node={node['id']}")
            continue
        if result["state"].get("view") != node["view"]:
            failures.append(f"{label} did not set the stage view to {node['view']!r}")
        if result["state"].get("node") != node["id"]:
            failures.append(f"{label} did not set Stage.state().node")
        if result["children"] != node["children"]:
            failures.append(f"{label} lists {result['children']} children, expected {node['children']}")
        if result["crumbs"] < 1:
            failures.append(f"{label} shows no breadcrumb")
        item = evaluate(diagnostics_script("interactive"))
        item["node"] = node["id"]
        item["viewport"] = "1440x900"
        diagnostics.append(item)
        path = bundle / f"node-{node['id']}.png"
        browse("screenshot", str(path))
        screenshots.append(path)

    root = evaluate("(document.querySelector('article.node:not([data-parent])') || {dataset: {}}).dataset.node || ''")
    browse("open", page_url)
    browse("wait", "500")
    browse("click", "#map-btn")
    browse("wait", "400")
    if evaluate("location.hash") != f"#node={root}":
        failures.append("map button did not open the root node")
    browse("open", f"{page_url}#node={root}")
    browse("wait", "500")
    stage_openers = evaluate(
        "JSON.stringify([...document.querySelectorAll('#stage [data-open-node]')].map(el => el.getAttribute('data-open-node')))"
    )
    if not stage_openers:
        failures.append("the stage has no clickable parts (data-open-node) in the root node view")
    else:
        target = stage_openers[0]
        evaluate(
            f"(() => {{ document.querySelector(\"#stage [data-open-node='{target}']\")"
            ".dispatchEvent(new MouseEvent('click', {bubbles: true})); return true; })()"
        )
        browse("wait", "400")
        if evaluate("location.hash") != f"#node={target}":
            failures.append(f"clicking stage part {target} did not open its node")
    browse("click", "#tour-btn")
    browse("wait", "500")
    if evaluate("document.body.classList.contains('drill')") is not False:
        failures.append("back-to-tour button did not leave drill-down")


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
      const small = visible.filter(el => {{
        const text = (el.textContent || '').trim();
        if (!text || el.children.length) return false;
        return parseFloat(getComputedStyle(el).fontSize) < 12;
      }});
      const tinyGroups = new Map();
      for (const el of small) {{
        const owner = el.closest('pre code') || el;
        const key = selector(owner) + ':' + getComputedStyle(el).fontSize;
        const group = tinyGroups.get(key) || {{selector: selector(owner),
          px: getComputedStyle(el).fontSize, count: 0, text: owner.textContent.trim().slice(0,80)}};
        group.count++;
        tinyGroups.set(key, group);
      }}
      const tinyText = [...tinyGroups.values()];
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


def browser_batch(agent_browser: str, session: str, commands: list[list[str]]) -> list[dict]:
    # JSON stdin preserves JavaScript quotes; batch's shell-style arguments do not.
    result = subprocess.run(
        browser_command(agent_browser, session, "--json", "batch"),
        input=json.dumps(commands), text=True, capture_output=True, timeout=120,
        env={**os.environ, "AGENT_BROWSER_DEFAULT_TIMEOUT": "5000"},
    )
    try:
        items = json.loads(result.stdout)
        if (not isinstance(items, list) or len(items) != len(commands)
                or any(not isinstance(item, dict) or not isinstance(item.get("success"), bool) for item in items)):
            raise ValueError("incomplete batch response")
        return items
    except (ValueError, TypeError) as error:
        raise ValueError(f"Browser batch failed: {result.stderr.strip()[:500] or str(error)}") from error


def batch_value(item: dict):
    if not item.get("success"):
        raise ValueError(item.get("error") or "browser command failed")
    value = item.get("result", {}).get("result")
    return parse_eval(json.dumps(value))


def prepare_script() -> str:
    # Disable motion only in this verification session, not in the artifact.
    return """(async () => {
      if (!document.getElementById('presentation-verify-motion')) {
        const style = document.createElement('style');
        style.id = 'presentation-verify-motion';
        style.textContent = '*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}';
        document.head.append(style);
      }
      await document.fonts.ready;
      await Promise.all([...document.images].map(img => img.decode().catch(() => {})));
      return true;
    })()"""


def slide_script(index: int) -> str:
    return f"""(async () => {{
      location.hash = '#page-{index}';
      const slides = [...document.querySelectorAll('.slide')];
      const deadline = performance.now() + 2000;
      while (!slides[{index - 1}]?.classList.contains('active') && performance.now() < deadline)
        await new Promise(resolve => setTimeout(resolve, 20));
      if (!slides[{index - 1}]?.classList.contains('active'))
        throw new Error('slide {index} did not become active');
      await new Promise(requestAnimationFrame);
      return true;
    }})()"""


def verify_deck(agent_browser: str, session: str, page_url: str, bundle: Path,
                screenshots: list[Path], diagnostics: list[dict], failures: list[str],
                selected: list[int] | None, skip_interactions: bool, *,
                _viewports: tuple | None = None, _interactions_only: bool = False,
                _control_partition: tuple[int, int] = (0, 1), _control_workers: int = 4) -> None:
    if _viewports is None:
        # Separate sessions prevent viewport changes and modals racing screenshots.
        jobs = [((viewport,), False, (0, 1)) for viewport in ((1440, 900), (1263, 863))]
        if not skip_interactions:
            workers = _control_workers
            jobs.extend(((), True, (index, workers)) for index in range(workers))

        def worker(viewports: tuple, interactions_only: bool, partition: tuple):
            worker_session = f"{session}-{uuid4().hex[:8]}"
            images, items, errors = [], [], []
            try:
                run_browser(browser_command(agent_browser, worker_session, "open", page_url))
                run_browser(browser_command(agent_browser, worker_session, "eval", prepare_script()))
                verify_deck(agent_browser, worker_session, page_url, bundle, images, items, errors,
                            selected, not interactions_only, _viewports=viewports,
                            _interactions_only=interactions_only, _control_partition=partition)
                page_errors = run_browser(browser_command(agent_browser, worker_session, "errors"), capture=True)
                if page_errors and "No page errors" not in page_errors:
                    errors.append("browser page errors: " + page_errors[:500])
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                errors.append(f"browser worker incomplete: {getattr(error, 'stderr', None) or str(error)}")
            finally:
                try:
                    run_browser(browser_command(agent_browser, worker_session, "close"))
                except (OSError, subprocess.SubprocessError) as error:
                    errors.append(f"browser cleanup failed: {error}")
            return images, items, errors

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = [pool.submit(worker, *job) for job in jobs]
            for future in futures:
                images, items, errors = future.result()
                screenshots.extend(images)
                diagnostics.extend(items)
                failures.extend(errors)
        return
    metadata = parse_eval(run_browser(browser_command(agent_browser, session, "eval",
        "JSON.stringify({count: document.querySelectorAll('.slide').length, controls: "
        # DOM-position selectors survive reloads without temporary attributes.
        "[...document.querySelectorAll('[data-verify-target]')].map((el,i)=>{"
        "let node=el, parts=[]; while(node && node!==document.body){"
        "parts.unshift(node.tagName.toLowerCase()+':nth-child('+"
        "([...node.parentElement.children].indexOf(node)+1)+')'); node=node.parentElement;}"
        "return {i,selector:'body > '+parts.join(' > '), target:el.dataset.verifyTarget,"
        "slide:[...document.querySelectorAll('.slide')].indexOf(el.closest('.slide'))+1}})})"
    ), capture=True))
    count = metadata["count"]
    slides = selected if selected is not None else list(range(1, count + 1))
    if not slides or any(index < 1 or index > count for index in slides):
        raise ValueError(f"--slides must contain slide numbers from 1 to {count}")

    def collect(commands: list[list[str]], label: str) -> list[dict]:
        try:
            return browser_batch(agent_browser, session, commands)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            failures.append(f"{label}: {error}")
            return []

    for width, height in _viewports:
        viewport = f"{width}x{height}"
        prefix = [["set", "viewport", str(width), str(height)], ["eval", prepare_script()]]
        groups = []
        for index in slides:
            path = bundle / f"slide-{index:02d}-{viewport}.png"
            groups.append((index, path, [["eval", slide_script(index)],
                          ["screenshot", str(path)], ["eval", diagnostics_script("deck")]]))
        results = collect(prefix + [cmd for _, _, group in groups for cmd in group], viewport)
        for offset, (index, path, group) in enumerate(groups):
            label = f"slide {index} at {viewport}"
            items = results[2 + offset * 3: 5 + offset * 3] if results else []
            if not items or not all(item.get("success") for item in results[:2] + items):
                # Retry the whole state after a fresh load; never retry a bare click.
                retry = collect([["open", page_url]] + prefix + group, label)
                if len(retry) != 6 or not all(item.get("success") for item in retry):
                    errors = [item.get("error") for item in (retry or items) if not item.get("success")]
                    failures.append(f"{label}: browser step failed: {errors}")
                    continue
                items = retry[-3:]
            screenshots.append(path)
            item = batch_value(items[2])
            item.update(slide=index, viewport=viewport)
            diagnostics.append(item)

    if skip_interactions:
        return
    navigation = collect([
        ["set", "viewport", "1440", "900"], ["eval", slide_script(1)],
        ["click", "#next-btn"], ["eval", "location.hash"],
        ["press", "ArrowLeft"], ["eval", "location.hash"],
    ], "navigation")
    if navigation:
        for item in navigation:
            if not item.get("success"):
                failures.append(f"navigation: {item.get('error')}")
        if navigation[3].get("success") and count > 1 and batch_value(navigation[3]) != "#page-2":
            failures.append("next navigation did not reach slide 2")
        if navigation[5].get("success") and batch_value(navigation[5]) != "#page-1":
            failures.append("keyboard previous navigation did not reach slide 1")

    for control in metadata["controls"]:
        if control["i"] % _control_partition[1] != _control_partition[0]:
            continue
        if selected is not None and control["slide"] not in slides:
            continue
        label = f"control {control['i'] + 1} (slide {control['slide']})"
        if control["slide"] < 1:
            failures.append(f"{label}: outside any slide")
            continue
        selector = control["selector"]
        target = json.dumps(control["target"])
        visible = f"(() => {{const el=document.querySelector({target}); if(!el) throw new Error('missing target'); const r=el.getBoundingClientRect(); return getComputedStyle(el).visibility !== 'hidden' && r.width>0 && r.height>0;}})()"
        path = bundle / f"interaction-{control['i'] + 1:02d}.png"
        # Reload each control to prevent hidden state from leaking between checks.
        commands = [["open", page_url], ["eval", prepare_script()],
                    ["eval", slide_script(control["slide"])], ["eval", visible],
                    ["click", selector], ["wait", "--fn", visible], ["eval", visible],
                    ["screenshot", str(path)], ["press", "Escape"],
                    ["wait", "--fn", f"!({visible})"], ["eval", visible]]
        results = collect(commands, label)
        if results and not all(item.get("success") for item in results):
            results = collect(commands, label + " retry")
        if not results:
            continue
        for command, item in zip(commands, results):
            if not item.get("success"):
                failures.append(f"{label}: {command[0]} failed: {item.get('error')}")
        if results[7].get("success"):
            screenshots.append(path)
        if all(results[i].get("success") for i in (3, 6, 10)):
            if batch_value(results[3]) is not False or batch_value(results[6]) is not True:
                failures.append(f"{label}: did not open {control['target']}")
            if batch_value(results[10]) is not False:
                failures.append(f"{label}: {control['target']} did not close with Escape")


def verify(format_name: str, output: Path, *, bundle_dir: Path | None = None,
           slides: list[int] | None = None, skip_interactions: bool = False) -> None:
    lint(format_name, output)
    agent_browser = shutil.which("agent-browser")
    if agent_browser is None:
        raise ValueError("agent-browser is required for browser verification")

    if format_name != "deck" and (slides is not None or skip_interactions):
        raise ValueError("--slides and --skip-interactions currently support only decks")
    started = time.perf_counter()
    bundle = (bundle_dir or output.with_name(f"{output.stem}.verification")).resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    page_url = output.resolve().as_uri() + f"?verify={uuid4().hex}"
    session = f"presentation-verify-{uuid4().hex[:12]}"
    screenshots: list[Path] = []
    diagnostics: list[dict] = []
    failures: list[str] = []

    try:
        if format_name != "deck":
            run_browser(browser_command(agent_browser, session, "open", page_url))
            run_browser(browser_command(agent_browser, session, "eval", prepare_script()))
        if format_name == "deck":
            parser = ArtifactHTMLParser()
            parser.feed(output.read_text(encoding="utf-8"))
            verify_deck(agent_browser, session, page_url, bundle, screenshots, diagnostics,
                        failures, slides, skip_interactions,
                        _control_workers=max(1, min(4, parser.verify_controls)))
        elif format_name == "interactive":
            verify_interactive(agent_browser, session, page_url, bundle, screenshots, diagnostics, failures)
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

        if format_name != "deck":
            errors = run_browser(browser_command(agent_browser, session, "errors"), capture=True)
            if errors and "No page errors" not in errors:
                failures.append("browser page errors: " + errors[:500])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        failures.append("browser verification incomplete: " + str(detail)[:500])
    finally:
        try:
            if format_name != "deck":
                run_browser(browser_command(agent_browser, session, "close"))
        except (OSError, subprocess.SubprocessError) as error:
            failures.append(f"browser cleanup failed: {error}")

    for item in diagnostics:
        if item.get("slide"):
            label = f"slide {item['slide']} at {item.get('viewport')}"
        elif item.get("chapter"):
            label = f"chapter {item['chapter']} at {item.get('viewport')}"
        else:
            label = f"page at {item.get('viewport')}"
        for key in ("clipped", "tinyText", "svgOverflow", "containerOverflow",
                    "wrappedCompactLabels", "inlineLabelBody",
                    "fixedChromeIntersections", "unlabeledButtons"):
            if item.get(key):
                failures.append(f"{label}: {key}: {item[key]}")
        if item.get("rootOverflow"):
            failures.append(f"{label}: unexpected root overflow")

    report = {"artifact": str(output), "format": format_name, "diagnostics": diagnostics,
              "failures": failures, "elapsed_seconds": round(time.perf_counter() - started, 3),
              "scope": {"slides": slides, "skip_interactions": skip_interactions},
              "screenshots": [path.name for path in screenshots]}
    (bundle / "diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    contact = write_contact_sheet(bundle, screenshots, report)
    if failures:
        raise ValueError("Browser verification failed:\n- " + "\n- ".join(failures) + f"\nEvidence: {contact}")
    scope = " (partial check)" if slides is not None or skip_interactions else ""
    print(f"Browser-verified {format_name} artifact{scope}: {output}")
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
        if command == "verify":
            subparser.add_argument("--bundle-dir", type=Path)
            subparser.add_argument("--slides", help="Comma-separated deck slide numbers; partial check")
            subparser.add_argument("--skip-interactions", action="store_true", help="Deck geometry only; partial check")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            initialize(args.format, args.output)
        elif args.command == "lint":
            lint(args.format, args.output)
        elif args.command == "verify":
            slides = list(dict.fromkeys(int(value) for value in args.slides.split(','))) if args.slides is not None else None
            verify(args.format, args.output, bundle_dir=args.bundle_dir,
                   slides=slides, skip_interactions=args.skip_interactions)
        elif args.format != "page":
            raise ValueError("Export currently supports only page format")
        else:
            export_page(args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
