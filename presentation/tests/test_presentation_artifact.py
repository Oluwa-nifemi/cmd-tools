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


if __name__ == "__main__":
    unittest.main()
