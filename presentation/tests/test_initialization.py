import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "presentation_artifact.py"
SPEC = importlib.util.spec_from_file_location("presentation_initializer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InitializationTests(unittest.TestCase):
    def test_deck_copies_assets_and_resolves_references_from_nested_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "deck.html"
            MODULE.initialize("deck", output)
            text = output.read_text()
            self.assertNotIn("cdnjs.cloudflare.com", text)
            for name in MODULE.HIGHLIGHT_FILES:
                relative = MODULE.HIGHLIGHT_ASSETS / name
                self.assertEqual((output.parent / relative).read_bytes(),
                                 (MODULE.ROOT / relative).read_bytes())
                if name != "LICENSE":
                    self.assertIn(relative.as_posix(), text)

    def test_reinitialization_backs_up_previous_html_and_keeps_versioned_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            MODULE.initialize("deck", output)
            output.write_text("Accepted deck")
            unrelated = output.parent / "assets" / "other.txt"
            unrelated.write_text("Keep me")
            MODULE.initialize("deck", output)
            backups = list((output.parent / ".presentation-backups").glob("*.html"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "Accepted deck")
            self.assertEqual(unrelated.read_text(), "Keep me")
            for name in MODULE.HIGHLIGHT_FILES:
                relative = MODULE.HIGHLIGHT_ASSETS / name
                self.assertEqual((output.parent / relative).read_bytes(),
                                 (MODULE.ROOT / relative).read_bytes())

    def test_missing_bundled_file_does_not_replace_existing_html_or_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.html"
            MODULE.initialize("deck", output)
            before = {path: path.read_bytes() for path in output.parent.rglob("*") if path.is_file()}
            with patch.object(MODULE, "HIGHLIGHT_FILES", (*MODULE.HIGHLIGHT_FILES, "missing.js")):
                with self.assertRaisesRegex(ValueError, "Missing bundled asset"):
                    MODULE.initialize("deck", output)
            after = {path: path.read_bytes() for path in output.parent.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_other_formats_do_not_copy_highlighting_assets(self):
        for format_name in ("page", "interactive"):
            with self.subTest(format=format_name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "artifact.html"
                MODULE.initialize(format_name, output)
                self.assertFalse((output.parent / MODULE.HIGHLIGHT_ASSETS).exists())


if __name__ == "__main__":
    unittest.main()
