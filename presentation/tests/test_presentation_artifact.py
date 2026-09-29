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


INTERACTIVE_SHELL = """<!doctype html><html><head><base target="_blank"></head><body>
<button data-depth="overview">Overview</button><button id="explore-btn">Explore</button>
<div id="stage"></div><p id="honesty">Traces are illustrative.</p>
<section id="story">{chapters}</section>
<script>window.Stage = {{}};</script></body></html>"""


def interactive_artifact(directory: str, chapters: str) -> Path:
    output = Path(directory) / "interactive.html"
    output.write_text(INTERACTIVE_SHELL.format(chapters=chapters))
    return output


class InteractiveLintTests(unittest.TestCase):
    def test_accepts_chapter_with_claim_and_go_deeper(self) -> None:
        chapters = """<article class="chapter" id="c1" data-view="a">
<h2>One</h2><p class="claim">The stage is small.</p>
<details class="deeper"><summary>Go deeper</summary>Formula.</details></article>"""
        with tempfile.TemporaryDirectory() as directory:
            MODULE.lint("interactive", interactive_artifact(directory, chapters))

    def test_rejects_chapter_without_visible_claim(self) -> None:
        chapters = """<article class="chapter" id="c1" data-view="a"><h2>One</h2>
<p class="claim"></p></article>"""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "chapter 1 needs a visible claim"):
                MODULE.lint("interactive", interactive_artifact(directory, chapters))

    def test_rejects_details_outside_go_deeper(self) -> None:
        chapters = """<article class="chapter" id="c1" data-view="a">
<p class="claim">Claim.</p><details><summary>More</summary></details></article>"""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "details only for Go deeper"):
                MODULE.lint("interactive", interactive_artifact(directory, chapters))

    def test_requires_honesty_label(self) -> None:
        chapters = '<article class="chapter" id="c1" data-view="a"><p class="claim">C.</p></article>'
        with tempfile.TemporaryDirectory() as directory:
            output = interactive_artifact(directory, chapters)
            output.write_text(output.read_text().replace('id="honesty"', ""))
            with self.assertRaisesRegex(ValueError, 'id="honesty"'):
                MODULE.lint("interactive", output)

    def test_initialized_template_fails_until_sample_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "interactive.html"
            MODULE.initialize("interactive", output)
            with self.assertRaisesRegex(ValueError, "template instructions"):
                MODULE.lint("interactive", output)


class DrillDownLintTests(unittest.TestCase):
    CHAPTER = '<article class="chapter" id="c1" data-view="a"><p class="claim">C.</p></article>'

    def node(self, node_id: str, parent: str | None = None, claim: str = "Claim.", view: str = "map") -> str:
        parent_attr = f' data-parent="{parent}"' if parent else ""
        return (f'<article class="node" id="node-{node_id}" data-node="{node_id}"{parent_attr} '
                f'data-level="component" data-view="{view}"><h2>{node_id}</h2><p class="claim">{claim}</p></article>')

    def lint_nodes(self, nodes: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            MODULE.lint("interactive", interactive_artifact(directory, self.CHAPTER + nodes))

    def test_accepts_tree_with_one_root_and_openers(self) -> None:
        stage_link = '<span data-open-node="api">API</span>'
        self.lint_nodes(self.node("system") + self.node("api", "system") + self.node("routes", "api") + stage_link)

    def test_rejects_missing_parent(self) -> None:
        with self.assertRaisesRegex(ValueError, "node api has unknown parent ghost"):
            self.lint_nodes(self.node("system") + self.node("api", "ghost"))

    def test_rejects_more_than_one_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one root node"):
            self.lint_nodes(self.node("system") + self.node("other"))

    def test_rejects_cycle(self) -> None:
        with self.assertRaisesRegex(ValueError, "node a is not reachable from the root"):
            self.lint_nodes(self.node("system") + self.node("a", "b") + self.node("b", "a"))

    def test_rejects_opener_to_unknown_node(self) -> None:
        with self.assertRaisesRegex(ValueError, "data-open-node points to unknown node nope"):
            self.lint_nodes(self.node("system") + '<button data-open-node="nope">x</button>')

    def test_rejects_node_without_claim(self) -> None:
        with self.assertRaisesRegex(ValueError, "node api needs a visible claim"):
            self.lint_nodes(self.node("system") + self.node("api", "system", claim=""))

    def test_rejects_duplicate_or_malformed_node_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "node id Bad_Id must use lowercase letters, digits, and hyphens"):
            self.lint_nodes(self.node("system") + self.node("Bad_Id", "system"))


class StageControlTests(unittest.TestCase):
    def test_parse_eval_keeps_plain_strings(self) -> None:
        self.assertEqual(MODULE.parse_eval('"#node=api"'), "#node=api")
        self.assertEqual(MODULE.parse_eval('"[\\"api\\"]"'), ["api"])
        self.assertIs(MODULE.parse_eval("true"), True)

    def test_control_that_changes_nothing_fails(self) -> None:
        self.assertEqual(
            MODULE.control_failures("control 1", {"view": "a"}, {"view": "a"}, []),
            ["control 1 did not change the stage"],
        )

    def test_control_that_changes_undeclared_keys_fails(self) -> None:
        before = {"view": "a", "example": "spider", "trace": "spider"}
        after = {"view": "a", "example": "ant", "trace": None}
        self.assertEqual(
            MODULE.control_failures("control 2", before, after, ["example"]),
            ["control 2 changed undeclared stage keys: trace"],
        )

    def test_control_with_declared_change_passes(self) -> None:
        self.assertEqual(
            MODULE.control_failures("control 3", {"example": "spider"}, {"example": "ant"}, ["example"]),
            [],
        )


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
