import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "presentation_artifact.py"
SPEC = importlib.util.spec_from_file_location("presentation_artifact", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VerifyTests(unittest.TestCase):
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
                MODULE.verify("deck", output)

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
                MODULE.verify("deck", output)


class VisualizationTests(unittest.TestCase):
    def test_initializer_selects_visualization_and_backs_up_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "visualization.html"
            output.write_text("previous user content")
            MODULE.initialize("visualization", output)
            self.assertEqual(output.read_text(), MODULE.TEMPLATES["visualization"].read_text())
            backups = list((output.parent / ".presentation-backups").glob("*.html"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "previous user content")

    def test_filled_visualization_passes_shell_check(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "visualization.html"
            text = MODULE.TEMPLATES["visualization"].read_text()
            output.write_text(text.replace("HEADING_PLACEHOLDER", "A process").replace("SUMMARY_PLACEHOLDER", "Follow one item."))
            MODULE.verify("visualization", output)

    def test_rejects_visualization_without_live_status(self):
        text = MODULE.TEMPLATES["visualization"].read_text().replace('aria-live="polite"', '')
        self.assertIn("an accessible live status region", MODULE.structural_failures("visualization", text))


if __name__ == "__main__":
    unittest.main()
