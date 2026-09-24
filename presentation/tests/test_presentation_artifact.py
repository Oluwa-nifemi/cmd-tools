import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "presentation_artifact.py"
SPEC = importlib.util.spec_from_file_location("presentation_artifact", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VerifyTests(unittest.TestCase):
    def test_page_requires_landscape_print_orientation(self) -> None:
        portrait = """<!doctype html><html><head><base target="_blank">
<style>@page { size: auto; } @media print {}</style></head><body>
<nav class="toc"></nav><section class="section"></section>
<button class="export-btn"></button></body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "page.html"
            output.write_text(portrait)
            with self.assertRaisesRegex(ValueError, "landscape PDF orientation"):
                MODULE.lint("page", output)

    def test_page_requires_section_pagination_and_export_links(self) -> None:
        missing_exports = """<!doctype html><html><head><base target="_blank">
<style>@page { size: A4 landscape; } @media print {}</style></head><body>
<nav class="toc"></nav><section class="section"></section>
<button class="export-btn"></button></body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "page.html"
            output.write_text(missing_exports)
            with self.assertRaisesRegex(ValueError, "section-pdf-link"):
                MODULE.lint("page", output)

    def test_rejects_template_instructions_exposed_by_malformed_comment(self) -> None:
        malformed = """<!doctype html>
<html><head><base target="_blank"><style>@media print {}</style></head>
<body><!-- PRESENTATION TEMPLATE. Replace content between <!-- SLIDES:START -->
HOW TO USE: replace everything between START and END -->
<section class="slide cover"></section>
<script>window.location.hash; addEventListener('hashchange', () => {});</script>
<button id="export-btn"></button></body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            output.write_text(malformed)
            with self.assertRaisesRegex(ValueError, "browser-visible template instructions"):
                MODULE.lint("deck", output)

    def test_rejects_duplicate_html_documents(self) -> None:
        duplicate = """<!doctype html><html><head><base target="_blank">
<style>@media print {}</style></head><body>
<section class="slide cover"></section><button id="export-btn"></button>
<script>window.location.hash; addEventListener('hashchange', () => {});</script>
</body></html><html><head></head><body></body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            output.write_text(duplicate)
            with self.assertRaisesRegex(ValueError, "exactly one <html>"):
                MODULE.lint("deck", output)

    def test_rejects_legacy_details_in_decks(self) -> None:
        deck = """<!doctype html><html><head><base target="_blank">
<style>@media print {}</style></head><body>
<section class="slide cover"><details><summary>More</summary></details></section>
<button id="export-btn"></button>
<script>window.location.hash; addEventListener('hashchange', () => {});</script>
</body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            output.write_text(deck)
            with self.assertRaisesRegex(ValueError, "must not use details"):
                MODULE.lint("deck", output)

    def test_rejects_duplicate_ids(self) -> None:
        deck = """<!doctype html><html><head><base target="_blank">
<style>@media print {}</style></head><body>
<section class="slide cover"><p id="same"></p><p id="same"></p></section>
<button id="export-btn"></button>
<script>window.location.hash; addEventListener('hashchange', () => {});</script>
</body></html>"""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            output.write_text(deck)
            with self.assertRaisesRegex(ValueError, "duplicates: same"):
                MODULE.lint("deck", output)


class ExportTests(unittest.TestCase):
    def test_page_export_paths_use_html_stem(self) -> None:
        output = Path("/tmp/review.html")

        self.assertEqual(
            MODULE.page_export_paths(output),
            (Path("/tmp/review-sections.pdf"), Path("/tmp/review-long.png")),
        )

    @patch.object(MODULE, "lint")
    @patch.object(MODULE, "chrome_executable", return_value="/chrome")
    @patch.object(MODULE.shutil, "which", return_value="/agent-browser")
    @patch.object(MODULE, "run_browser", side_effect=["2", "", ""])
    @patch.object(MODULE.subprocess, "run")
    def test_export_page_generates_pdf_and_full_height_png(
        self,
        run: Mock,
        run_browser: Mock,
        _which: Mock,
        _chrome: Mock,
        lint: Mock,
    ) -> None:
        output = Path("/tmp/review.html")
        page_url = output.resolve().as_uri()

        MODULE.export_page(output)

        lint.assert_called_once_with("page", output)
        self.assertEqual(
            run.call_args_list,
            [
                call(
                    [
                        "/chrome",
                        "--headless",
                        "--disable-gpu",
                        "--no-pdf-header-footer",
                        "--print-to-pdf=/tmp/review-sections.pdf",
                        page_url,
                    ],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "--allow-file-access", "open", page_url],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "set", "viewport", "1440", "1100", "2"],
                    check=True,
                ),
                call(
                    [
                        "/agent-browser",
                        "--session",
                        "presentation-export-review",
                        "eval",
                        "document.getElementById('page-comment-controls').style.display='none'",
                    ],
                    check=True,
                ),
                call(
                    [
                        "/agent-browser",
                        "--session",
                        "presentation-export-review",
                        "screenshot",
                        "--full",
                        "/tmp/review-long.png",
                    ],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "screenshot", "/tmp/review-section-images/section-01.png"],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "screenshot", "/tmp/review-section-images/section-02.png"],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "close"],
                    check=False,
                ),
            ],
        )
        self.assertEqual(run_browser.call_count, 3)


if __name__ == "__main__":
    unittest.main()
