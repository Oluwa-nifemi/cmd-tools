import importlib.util
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "presentation_artifact.py"
SPEC = importlib.util.spec_from_file_location("presentation_artifact", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
VERIFY_DECK = MODULE.verify_deck


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


class BrowserCommandTests(unittest.TestCase):
    def test_verification_commands_keep_isolated_namespace_and_pinned_tab(self) -> None:
        actions = (("open", "file:///deck.html"), ("eval", "true"),
                   ("--json", "batch"), ("errors",), ("close",))
        for name in ("abc123", "abc123-worker1", "abc123-worker2"):
            for action in actions:
                with self.subTest(name=name, action=action):
                    self.assertEqual(
                        MODULE.browser_command("/browser", "presentation-verify-" + name, *action),
                        ["/browser", "--session", name, "--namespace", name,
                         "--pin-tab", "--no-webmcp", "--headed", "false",
                         "--args", "--disable-quic",
                         "--allow-file-access", *action],
                    )

    def test_non_verification_sessions_keep_their_names_and_flags(self) -> None:
        for session in ("test", "presentation-export-review", "other-presentation-verify-name"):
            with self.subTest(session=session):
                self.assertEqual(MODULE.browser_command("/browser", session, "close"),
                                 ["/browser", "--session", session, "--allow-file-access", "close"])


class BrowserBatchTests(unittest.TestCase):
    @patch.object(MODULE.subprocess, "run")
    def test_json_stdin_preserves_quotes_and_middle_failure(self, run: Mock) -> None:
        commands = [
            ["eval", "document.querySelector('[data-name=\"a b\"]').textContent"],
            ["click", "#missing"],
            ["eval", "JSON.stringify({text: \"it's quoted\", path: 'a\\b'})"],
        ]
        items = [
            {"success": True, "result": {"result": "a b"}},
            {"success": False, "error": "missing selector"},
            {"success": True, "result": {"result": "later state"}},
        ]
        run.return_value = subprocess.CompletedProcess([], 1, json.dumps(items), "")

        self.assertEqual(MODULE.browser_batch("/browser", "test", commands), items)
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["/browser", "--session", "test",
                                   "--allow-file-access", "--json", "batch"])
        self.assertEqual(json.loads(kwargs["input"]), commands)
        self.assertTrue(kwargs["text"])
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(MODULE.batch_value(items[2]), "later state")
        with self.assertRaisesRegex(ValueError, "missing selector"):
            MODULE.batch_value(items[1])

    @patch.object(MODULE.subprocess, "run")
    def test_rejects_malformed_missing_or_wrong_length_batch(self, run: Mock) -> None:
        commands = [["eval", "true"], ["eval", "false"]]
        for stdout in ("", "not json", "null", "{}", "[]",
                       '[{"success": true}]', '[{}, {}, {}]'):
            with self.subTest(stdout=stdout):
                run.return_value = subprocess.CompletedProcess([], 0, stdout, "")
                with self.assertRaisesRegex(ValueError, "Browser batch failed:"):
                    MODULE.browser_batch("/browser", "test", commands)

    @patch.object(MODULE.subprocess, "run")
    def test_invalid_response_reports_browser_stderr(self, run: Mock) -> None:
        run.return_value = subprocess.CompletedProcess([], 1, "", " browser unavailable ")
        with self.assertRaisesRegex(ValueError, "Browser batch failed: browser unavailable"):
            MODULE.browser_batch("/browser", "test", [["open", "file:///deck.html"]])


class BrowserEvidenceTests(unittest.TestCase):
    @patch.object(MODULE, "lint")
    @patch.object(MODULE.shutil, "which", return_value="/browser")
    def test_initial_failure_still_writes_evidence_and_closes(self, _which: Mock, _lint: Mock) -> None:
        errors = (OSError("launch failed"),
                  subprocess.CalledProcessError(1, ["open"], stderr="open failed"),
                  subprocess.TimeoutExpired(["open"], 60))
        for error in errors:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "interactive.html"
                bundle = Path(directory) / "evidence"
                with patch.object(MODULE, "run_browser", side_effect=[error, ""]) as browse, \
                     patch.object(MODULE, "verify_interactive") as interactive:
                    with self.assertRaisesRegex(ValueError, "browser verification incomplete"):
                        MODULE.verify("interactive", output, bundle_dir=bundle)
                interactive.assert_not_called()
                self.assertEqual(browse.call_args_list[0].args[0][-2], "open")
                self.assertEqual(browse.call_args_list[-1].args[0][-1], "close")
                report = json.loads((bundle / "diagnostics.json").read_text())
                self.assertEqual(report["screenshots"], [])
                self.assertEqual(report["diagnostics"], [])
                self.assertIn("browser verification incomplete", report["failures"][0])
                self.assertIn("browser verification incomplete", (bundle / "contact-sheet.html").read_text())

    @patch.object(MODULE, "lint")
    @patch.object(MODULE.shutil, "which", return_value="/browser")
    @patch.object(MODULE, "verify_interactive")
    def test_cleanup_failure_preserves_evidence(self, _interactive: Mock, _which: Mock, _lint: Mock) -> None:
        for initial_error in (None, OSError("launch failed")):
            with self.subTest(initial_error=initial_error), tempfile.TemporaryDirectory() as directory:
                bundle = Path(directory) / "evidence"
                responses = (["", "", "No page errors"] if initial_error is None else [initial_error])
                responses.append(subprocess.CalledProcessError(1, ["close"]))
                with patch.object(MODULE, "run_browser", side_effect=responses):
                    with self.assertRaisesRegex(ValueError, "browser cleanup failed"):
                        MODULE.verify("interactive", Path(directory) / "interactive.html", bundle_dir=bundle)
                report = json.loads((bundle / "diagnostics.json").read_text())
                self.assertTrue(any("browser cleanup failed" in failure for failure in report["failures"]))
                self.assertEqual(len(report["failures"]), 1 if initial_error is None else 2)
                self.assertIn("browser cleanup failed", (bundle / "contact-sheet.html").read_text())


    @patch.object(MODULE, "lint")
    @patch.object(MODULE.shutil, "which", return_value="/browser")
    def test_deck_failure_preserves_completed_evidence_without_parent_browser(
        self, _which: Mock, _lint: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "evidence"
            diagnostic = {"slide": 1, "viewport": "1440x900"}
            output = Path(directory) / "deck.html"
            output.write_text('<button data-verify-target="#modal">Open</button>')

            def deck(_browser, _session, _url, bundle, screenshots, diagnostics,
                     _failures, _selected, _skip_interactions, *, _control_workers):
                self.assertEqual(_control_workers, 1)
                screenshots.append(bundle / "slide-01-1440x900.png")
                diagnostics.append(diagnostic)
                raise OSError("later worker failed")

            with patch.object(MODULE, "verify_deck", side_effect=deck), \
                 patch.object(MODULE, "run_browser") as browse:
                with self.assertRaisesRegex(ValueError, "later worker failed"):
                    MODULE.verify("deck", output, bundle_dir=bundle)
            browse.assert_not_called()
            report = json.loads((bundle / "diagnostics.json").read_text())
            self.assertEqual(report["screenshots"], ["slide-01-1440x900.png"])
            self.assertEqual(report["diagnostics"], [diagnostic])
            self.assertEqual(report["failures"], ["browser verification incomplete: later worker failed"])
            contact = (bundle / "contact-sheet.html").read_text()
            self.assertIn("slide-01-1440x900.png", contact)
            self.assertIn("later worker failed", contact)


class DeckBrowserRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name) / "deck.html"
        self.output.write_text('<button data-verify-target="#modal">Open</button>')
        self.bundle = Path(directory.name) / "evidence"
        self.metadata = {"count": 3, "controls": []}
        for target, kwargs in (("lint", {}), ("run_browser", {"side_effect": self.browse})):
            patcher = patch.object(MODULE, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(MODULE.shutil, "which", return_value="/browser")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.serial_deck = patch.object(
            MODULE, "verify_deck",
            side_effect=lambda *args, **kwargs: VERIFY_DECK(
                *args, **kwargs, _viewports=((1440, 900), (1263, 863))),
        )
        self.serial_deck.start()
        self.addCleanup(self.serial_deck.stop)

    def browse(self, command: list[str], *, capture: bool = False) -> str:
        if not capture:
            return ""
        if command[-1] == "errors":
            return "No page errors"
        if command[-1] == "document.querySelectorAll('[data-verify-target]').length":
            return json.dumps(len(self.metadata["controls"]))
        if "JSON.stringify({count:" in command[-1]:
            return json.dumps(self.metadata)
        return json.dumps("body > button:nth-child(1)")

    def batch_results(self, commands: list[list[str]]) -> list[dict]:
        results = []
        hashes = iter(("#page-2", "#page-1"))
        for command in commands:
            value = {} if command == ["eval", MODULE.diagnostics_script("deck")] else True
            if command == ["eval", "location.hash"]:
                value = next(hashes)
            results.append({"success": True, "result": {"result": value}})
        return results

    def report(self) -> dict:
        return json.loads((self.bundle / "diagnostics.json").read_text())

    def test_partial_scope_reports_only_selected_slides_and_skips_interactions(self) -> None:
        def batch(_browser, _session, commands):
            return self.batch_results(commands)

        with patch.object(MODULE, "browser_batch", side_effect=batch) as batches, \
             patch("builtins.print") as print_result:
            MODULE.verify("deck", self.output, bundle_dir=self.bundle, slides=[2], skip_interactions=True)
        report = self.report()
        self.assertEqual(report["scope"], {"slides": [2], "skip_interactions": True})
        self.assertEqual([(item["slide"], item["viewport"]) for item in report["diagnostics"]],
                         [(2, "1440x900"), (2, "1263x863")])
        self.assertEqual(report["screenshots"], ["slide-02-1440x900.png", "slide-02-1263x863.png"])
        self.assertEqual(report["failures"], [])
        self.assertEqual(batches.call_count, 2)
        self.assertIn("partial check", print_result.call_args_list[0].args[0])
        contact = (self.bundle / "contact-sheet.html").read_text()
        for screenshot in report["screenshots"]:
            self.assertIn(screenshot, contact)

    def test_diagnostic_errors_include_slide_and_viewport(self) -> None:
        def batch(_browser, _session, commands):
            results = self.batch_results(commands)
            results[-1]["result"]["result"] = {"tinyText": ["#caption"], "rootOverflow": True}
            return results

        with patch.object(MODULE, "browser_batch", side_effect=batch):
            with self.assertRaisesRegex(ValueError, "slide 2 at 1440x900: tinyText"):
                MODULE.verify("deck", self.output, bundle_dir=self.bundle, slides=[2], skip_interactions=True)
        failures = self.report()["failures"]
        for viewport in ("1440x900", "1263x863"):
            self.assertIn(f"slide 2 at {viewport}: tinyText: ['#caption']", failures)
            self.assertIn(f"slide 2 at {viewport}: unexpected root overflow", failures)

    def test_failed_middle_slide_reloads_and_continues_later_states(self) -> None:
        for retry_succeeds in (True, False):
            with self.subTest(retry_succeeds=retry_succeeds):
                retries = []

                def batch(_browser, _session, commands):
                    results = self.batch_results(commands)
                    if commands[0][0] == "open":
                        retries.append(commands)
                        if not retry_succeeds:
                            results[4] = {"success": False, "error": "capture failed again"}
                    else:
                        results[6] = {"success": False, "error": "middle capture failed"}
                    return results

                with patch.object(MODULE, "browser_batch", side_effect=batch):
                    if retry_succeeds:
                        MODULE.verify("deck", self.output, bundle_dir=self.bundle, skip_interactions=True)
                    else:
                        with self.assertRaisesRegex(ValueError, "slide 2 at 1440x900: browser step failed"):
                            MODULE.verify("deck", self.output, bundle_dir=self.bundle, skip_interactions=True)
                report = self.report()
                expected_slides = [1, 2, 3] if retry_succeeds else [1, 3]
                self.assertEqual([item["slide"] for item in report["diagnostics"]], expected_slides * 2)
                self.assertEqual(len(report["screenshots"]), len(expected_slides) * 2)
                self.assertEqual(len(retries), 2)
                for commands in retries:
                    self.assertTrue(commands[0][1].startswith(self.output.resolve().as_uri() + "?verify="))
                    self.assertEqual(commands[1][0:2], ["set", "viewport"])
                    self.assertEqual(commands[2], ["eval", MODULE.prepare_script()])
                    self.assertEqual(commands[3], ["eval", MODULE.slide_script(2)])
                if retry_succeeds:
                    self.assertEqual(report["failures"], [])
                else:
                    for viewport in ("1440x900", "1263x863"):
                        self.assertTrue(any(f"slide 2 at {viewport}" in failure and
                                            "capture failed again" in failure for failure in report["failures"]))

    def test_missing_batch_recovers_each_slide_and_checks_next_viewport(self) -> None:
        first_batch = True

        def batch(_browser, _session, commands):
            nonlocal first_batch
            if first_batch:
                first_batch = False
                raise ValueError("Browser batch failed: incomplete batch response")
            return self.batch_results(commands)

        with patch.object(MODULE, "browser_batch", side_effect=batch) as batches:
            with self.assertRaisesRegex(ValueError, "1440x900: Browser batch failed"):
                MODULE.verify("deck", self.output, bundle_dir=self.bundle, skip_interactions=True)
        self.assertEqual(batches.call_count, 5)
        self.assertEqual([item["slide"] for item in self.report()["diagnostics"]], [1, 2, 3] * 2)
        self.assertEqual(len(self.report()["screenshots"]), 6)

    def test_failed_control_retries_whole_state_and_continues_next_control(self) -> None:
        self.metadata["controls"] = [
            {"i": 0, "slide": 1, "target": "#first-modal",
             "selector": "body > section:nth-child(1) > button:nth-child(1)"},
            {"i": 1, "slide": 3, "target": "#later-modal",
             "selector": "body > section:nth-child(3) > button:nth-child(1)"},
        ]
        interactions = []

        def batch(_browser, _session, commands):
            results = self.batch_results(commands)
            if len(commands) == 11 and commands[0][0] == "open":
                interactions.append(commands)
                for index, visible in ((3, False), (6, True), (10, False)):
                    results[index]["result"]["result"] = visible
                if "#first-modal" in commands[3][1]:
                    results[4] = {"success": False, "error": "click failed"}
            return results

        with patch.object(MODULE, "browser_batch", side_effect=batch):
            with self.assertRaisesRegex(ValueError, r"control 1 [(]slide 1[)]: click failed"):
                MODULE.verify("deck", self.output, bundle_dir=self.bundle)
        self.assertEqual(len(interactions), 3)
        self.assertEqual(interactions[0][0][0], "open")
        self.assertEqual(len(interactions[0]), 11)
        self.assertEqual(interactions[1][0][0], "open")
        self.assertTrue(interactions[1][0][1].startswith(self.output.resolve().as_uri() + "?verify="))
        self.assertEqual(interactions[0], interactions[1])
        self.assertEqual(interactions[2][0][0], "open")
        self.assertEqual(interactions[0][4], ["click", self.metadata["controls"][0]["selector"]])
        self.assertEqual(interactions[2][4], ["click", self.metadata["controls"][1]["selector"]])
        self.assertIn("#later-modal", interactions[2][3][1])
        report = self.report()
        self.assertIn("interaction-02.png", report["screenshots"])
        self.assertEqual(report["failures"], ["control 1 (slide 1): click failed: click failed"])

    def test_parallel_workers_use_isolated_sessions_and_merge_in_job_order(self) -> None:
        self.serial_deck.stop()
        self.output.write_text('<button data-verify-target="#modal">Open</button>' * 4)
        self.metadata["controls"] = [
            {"i": 0, "slide": 2, "target": "#modal",
             "selector": "body > section:nth-child(2) > button:nth-child(1)"},
        ]
        barrier = threading.Barrier(6, timeout=5)
        interaction_closed = threading.Event()
        narrow_closed = threading.Event()
        lock = threading.Lock()
        roles = {}
        completion_order = []
        lifecycle = []

        def batch(_browser, session, commands):
            session = session.removeprefix("presentation-verify-")
            role = ("interactions" if any(command == ["click", "#next-btn"] for command in commands)
                    else "x".join(commands[0][2:4]) if commands[0][:2] == ["set", "viewport"]
                    else "interactions")
            with lock:
                first_batch = session not in roles
                roles[session] = role
            if first_batch:
                barrier.wait()
            results = self.batch_results(commands)
            if len(commands) == 11 and commands[0][0] == "open":
                for index, visible in ((3, False), (6, True), (10, False)):
                    results[index]["result"]["result"] = visible
            return results

        def browse(command, *, capture=False):
            session = command[2]
            self.assertEqual(command[3:12], ["--namespace", session, "--pin-tab",
                                             "--no-webmcp", "--headed", "false",
                                             "--args", "--disable-quic", "--allow-file-access"])
            if command[-2] == "open" or command[-1] == "close":
                with lock:
                    lifecycle.append((session, "open" if command[-2] == "open" else "close"))
            role = roles.get(session)
            if command[-1] == "errors" and role:
                return role + " page error"
            if command[-1] == "close" and role:
                # Complete in reverse order so completion-order merging cannot pass.
                if role == "1440x900":
                    self.assertTrue(narrow_closed.wait(5), "narrow worker did not finish")
                elif role == "1263x863":
                    self.assertTrue(interaction_closed.wait(5), "interaction worker did not finish")
                with lock:
                    completion_order.append(role)
                    if completion_order.count("interactions") == 4:
                        interaction_closed.set()
                if role == "1263x863":
                    narrow_closed.set()
            return self.browse(command, capture=capture)

        with patch.object(MODULE, "browser_batch", side_effect=batch), \
             patch.object(MODULE, "run_browser", side_effect=browse):
            with self.assertRaisesRegex(ValueError, "browser page errors"):
                MODULE.verify("deck", self.output, bundle_dir=self.bundle)
        self.assertEqual(completion_order, ["interactions"] * 4 + ["1263x863", "1440x900"])
        self.assertEqual(len(roles), 6)
        self.assertEqual(set(roles.values()), {"1440x900", "1263x863", "interactions"})
        self.assertEqual({session for session, _action in lifecycle}, set(roles))
        for session in roles:
            self.assertEqual(lifecycle.count((session, "open")), 1)
            self.assertEqual(lifecycle.count((session, "close")), 1)
        report = self.report()
        self.assertEqual(report["scope"], {"slides": None, "skip_interactions": False})
        self.assertEqual([(item["slide"], item["viewport"]) for item in report["diagnostics"]],
                         [(slide, viewport) for viewport in ("1440x900", "1263x863")
                          for slide in (1, 2, 3)])
        expected_images = [f"slide-{slide:02d}-{viewport}.png"
                           for viewport in ("1440x900", "1263x863") for slide in (1, 2, 3)]
        expected_images.append("interaction-01.png")
        self.assertEqual(report["screenshots"], expected_images)
        self.assertEqual(report["failures"], [
            "browser page errors: 1440x900 page error",
            "browser page errors: 1263x863 page error",
        ] + ["browser page errors: interactions page error"] * 4)
        contact = (self.bundle / "contact-sheet.html").read_text()
        positions = [contact.index('href="' + name + '"') for name in expected_images]
        self.assertEqual(positions, sorted(positions))


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
                    ["/agent-browser", "--session", "presentation-export-review", "--allow-file-access", "screenshot", "/tmp/review-section-images/section-01.png"],
                    check=True,
                ),
                call(
                    ["/agent-browser", "--session", "presentation-export-review", "--allow-file-access", "screenshot", "/tmp/review-section-images/section-02.png"],
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
