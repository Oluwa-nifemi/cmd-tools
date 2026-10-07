import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "presentation_artifact.py"
TEMPLATES = {
    "deck": "template.html",
    "page": "page-template.html",
    "interactive": "interactive-template.html",
}


def create_artifact(format_name: str, output: Path) -> Path:
    output = Path(output)
    text = (ROOT / TEMPLATES[format_name]).read_text(encoding="utf-8")
    for old, new in {
        "TITLE_PLACEHOLDER": "Browser verification",
        "SUBTITLE_PLACEHOLDER": "Local browser regression checks.",
        "META_PLACEHOLDER": "2026-10-07",
        "Example slide — delete me": "Rendered evidence",
        "Example section — delete me": "Rendered evidence",
        "Example chapter — delete me": "An input produces twice its value",
    }.items():
        text = text.replace(old, new)
    # CDN availability must not decide whether a local interaction works.
    text = re.sub(r'<link\b[^>]*href="https://[^"]*"[^>]*>', "", text)
    text = re.sub(r'<script\b[^>]*src="https://[^"]*"[^>]*></script>', "", text)
    if format_name == "deck":
        slides = []
        for index in (1, 2):
            slides.append(
                f'<section class="slide{" cover" if index == 1 else ""}" data-title="Evidence {index}">'
                f'<h2 class="slide-title">Rendered evidence {index}</h2>'
                '<p>Each slide opens the same modal from a fresh state.</p>'
                f'<button id="evidence-{index}" class="see-code-btn" '
                'data-verify-target="#code-modal">View implementation excerpt</button>'
                # The template handler reads nextElementSibling, not a target ID.
                f'<div class="see-code-src"><pre><code>evidence {index}</code></pre></div>'
                '</section>'
            )
        text = re.sub(
            r'(<!-- SLIDES:START.*?-->).*?(<!-- SLIDES:END -->)',
            lambda match: match[1] + "\n" + "\n".join(slides) + "\n" + match[2],
            text, flags=re.S,
        )
    elif format_name == "page":
        text = re.sub(
            r'<section class="section" id="example-section">.*?</section>',
            '<section class="section" id="example-section">'
            '<h2 class="section-head">Rendered evidence</h2>'
            '<div class="section-body"><p>The reader can see this evidence without clicking.</p></div>'
            '</section>', text, flags=re.S,
        )
        text = text.replace('>Example section</a>', '>Rendered evidence</a>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


@unittest.skipUnless(os.environ.get("PRESENTATION_BROWSER_TESTS") == "1",
                     "set PRESENTATION_BROWSER_TESTS=1 to run real-browser tests")
class BrowserVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(shutil.which("agent-browser"), "agent-browser is required")
        self.directory = tempfile.TemporaryDirectory(prefix="presentation-browser-")
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "artifact.html"
        self.bundle = Path(self.directory.name) / "verification"

    def run_verifier(self, format_name: str, *, healthy: bool, extra: tuple = ()) -> dict:
        started = time.time()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", "--format", format_name,
             "--output", str(self.output), "--bundle-dir", str(self.bundle), *extra],
            capture_output=True, text=True, timeout=180,
        )
        ended = time.time()
        self.assertEqual(result.returncode, 0 if healthy else 1, result.stdout + result.stderr)
        report_path = self.bundle / "diagnostics.json"
        self.assertTrue(report_path.is_file(), result.stdout + result.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["artifact"], str(self.output))
        self.assertEqual(report["format"], format_name)
        self.assertGreater(report["elapsed_seconds"], 0)
        self.assertLessEqual(report["elapsed_seconds"], ended - started + 1)
        self.assertEqual(bool(report["failures"]), not healthy)
        self.assertTrue(report["diagnostics"])
        self.assertTrue(report["screenshots"])
        self.assertEqual(len(report["screenshots"]), len(set(report["screenshots"])))
        contact = self.bundle / "contact-sheet.html"
        contact_text = contact.read_text(encoding="utf-8")
        self.assertEqual(contact_text.count('<img '), len(report["screenshots"]))
        for path in [report_path, contact, *(self.bundle / name for name in report["screenshots"])]:
            with self.subTest(evidence=path.name):
                self.assertGreater(path.stat().st_size, 0)
                self.assertGreaterEqual(path.stat().st_mtime, started - 1)
                self.assertLessEqual(path.stat().st_mtime, ended + 1)
                if path.suffix == ".png":
                    with path.open("rb") as image:
                        self.assertEqual(image.read(8), b"\x89PNG\r\n\x1a\n")
                    self.assertIn(path.name, contact_text)
        if not healthy:
            self.assertIn("Browser verification failed", result.stderr)
            self.assertIn(str(contact), result.stderr)
        return report

    def deck(self, old: str = "", new: str = "") -> None:
        create_artifact("deck", self.output)
        if old:
            text = self.output.read_text(encoding="utf-8")
            self.assertIn(old, text)
            self.output.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_healthy_deck_checks_both_shared_modal_buttons(self) -> None:
        self.deck()
        report = self.run_verifier("deck", healthy=True)
        self.assertEqual(len(report["diagnostics"]), 4)
        self.assertEqual(len(report["screenshots"]), 6)
        self.assertEqual({(item["slide"], item["viewport"]) for item in report["diagnostics"]},
                         {(slide, viewport) for slide in (1, 2)
                          for viewport in ("1440x900", "1263x863")})
        self.assertIn("interaction-01.png", report["screenshots"])
        self.assertIn("interaction-02.png", report["screenshots"])
        self.assertEqual(report["scope"], {"slides": None, "skip_interactions": False})

    def test_healthy_page_checks_full_height_and_sections(self) -> None:
        create_artifact("page", self.output)
        report = self.run_verifier("page", healthy=True)
        self.assertEqual(len(report["diagnostics"]), 2)
        self.assertEqual(len(report["screenshots"]), 4)
        self.assertEqual({item["viewport"] for item in report["diagnostics"]},
                         {"1440x1100", "1263x863"})
        self.assertEqual(sum(name.startswith("page-full-") for name in report["screenshots"]), 2)
        self.assertEqual(sum(name.startswith("section-01-annotated-")
                             for name in report["screenshots"]), 2)

    def test_healthy_interactive_checks_chapter_controls_and_modes(self) -> None:
        create_artifact("interactive", self.output)
        report = self.run_verifier("interactive", healthy=True)
        self.assertEqual(len(report["diagnostics"]), 2)
        self.assertEqual(len(report["screenshots"]), 6)
        self.assertEqual({item["viewport"] for item in report["diagnostics"]},
                         {"1440x900", "1263x863"})
        for name in ("control-01.png", "control-02.png", "overview.png", "explore.png"):
            self.assertIn(name, report["screenshots"])

    def test_broken_next_navigation_fails(self) -> None:
        self.deck("addEventListener('click', next)", "addEventListener('click', function () {})")
        report = self.run_verifier("deck", healthy=False)
        self.assertTrue(any("next navigation" in failure for failure in report["failures"]))

    def test_overlay_blocks_real_click(self) -> None:
        self.deck('</body>',
                  '<div id="click-blocker" style="position:fixed;inset:0;z-index:9999"></div></body>')
        report = self.run_verifier("deck", healthy=False)
        self.assertTrue(any("control 1" in failure and "click failed" in failure
                            for failure in report["failures"]), report["failures"])

    def test_missing_modal_target_fails(self) -> None:
        self.deck('data-verify-target="#code-modal"', 'data-verify-target="#missing-modal"')
        report = self.run_verifier("deck", healthy=False)
        self.assertTrue(any("control 1" in failure and "missing target" in failure
                            for failure in report["failures"]), report["failures"])

    def test_escape_handler_failure_fails(self) -> None:
        self.deck("if (e.key === 'Escape') hideModal();", "if (e.key === 'Escape') return;")
        report = self.run_verifier("deck", healthy=False)
        self.assertTrue(any("control 1" in failure and
                            ("Escape" in failure or "wait failed" in failure)
                            for failure in report["failures"]), report["failures"])

    def test_tiny_highlighted_text_is_grouped_per_code_block(self) -> None:
        spans = " ".join('<span style="font-size:8px">token</span>' for _ in range(20))
        self.deck('<button id="evidence-1"', f'<pre><code id="tiny-code">{spans}</code></pre><button id="evidence-1"')
        report = self.run_verifier("deck", healthy=False, extra=("--skip-interactions",))
        items = [item for item in report["diagnostics"] if item["slide"] == 1]
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertEqual(len(item["tinyText"]), 1)
            self.assertEqual(item["tinyText"][0]["selector"], "#tiny-code")
            self.assertEqual(item["tinyText"][0]["count"], 20)
            self.assertEqual(item["tinyText"][0]["px"], "8px")
        self.assertEqual(len(report["screenshots"]), 4)

    def test_overflow_only_at_small_viewport_fails(self) -> None:
        self.deck('<button id="evidence-1"',
                  '<div id="wide-evidence" style="width:1100px;flex-shrink:0">Wide evidence</div><button id="evidence-1"')
        report = self.run_verifier("deck", healthy=False, extra=("--skip-interactions",))
        large, small = [next(item for item in report["diagnostics"]
                             if item["slide"] == 1 and item["viewport"] == viewport)
                        for viewport in ("1440x900", "1263x863")]
        self.assertNotIn("#wide-evidence", large["clipped"])
        self.assertFalse(large["rootOverflow"])
        self.assertTrue(small["rootOverflow"] or "#wide-evidence" in small["clipped"])
        self.assertTrue(any("1263x863" in failure for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()
