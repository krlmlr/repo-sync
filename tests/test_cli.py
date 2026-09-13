"""The two entry points as a contributor meets them: arguments, exit statuses, and the credential."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import collect_metrics
import render_dashboard
from portfolio import snapshot as snap

from tests.support import FIXTURES


class CredentialTest(unittest.TestCase):
    def test_the_environment_is_read_first(self):
        self.assertEqual(collect_metrics.resolve_token({"GITHUB_TOKEN": "from-actions"}), "from-actions")
        self.assertEqual(collect_metrics.resolve_token({"GH_TOKEN": "from-gh"}), "from-gh")

    def test_an_existing_gh_login_is_the_fallback(self):
        with mock.patch.object(collect_metrics.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout="gh-token\n")
            self.assertEqual(collect_metrics.resolve_token({}), "gh-token")

    def test_with_no_credential_the_message_names_both_ways_of_providing_one(self):
        with mock.patch.object(collect_metrics.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(collect_metrics.MissingCredential) as caught:
                collect_metrics.resolve_token({})
        message = str(caught.exception)
        self.assertIn("GITHUB_TOKEN", message)
        self.assertIn("gh auth login", message)

    def test_a_run_with_no_credential_says_what_to_do_and_collects_nothing(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        with mock.patch.object(collect_metrics, "resolve_token", side_effect=collect_metrics.MissingCredential("no token")):
            with mock.patch.object(collect_metrics, "UrllibTransport", side_effect=AssertionError("a request was made")):
                status = collect_metrics.main(
                    ["--repos", str(FIXTURES / "repos.yml"), "--out", str(directory / "metrics.json")]
                )
        self.assertEqual(status, 2)
        self.assertFalse((directory / "metrics.json").exists())


class MalformedInventoryTest(unittest.TestCase):
    def run_against(self, text: str) -> int:
        directory = Path(self.enterContext(TemporaryDirectory()))
        repos = directory / "repos.yml"
        repos.write_text(text)
        # Any request at all is a failure here: a malformed inventory is refused before the network.
        with mock.patch.object(collect_metrics, "UrllibTransport", side_effect=AssertionError("a request was made")):
            return collect_metrics.main(["--repos", str(repos), "--out", str(directory / "metrics.json")])

    def test_no_template_exits_non_zero_before_any_request(self):
        self.assertEqual(self.run_against("repos:\n  - org: a\n    repo: b\n"), 2)

    def test_two_templates_exit_non_zero_before_any_request(self):
        self.assertEqual(
            self.run_against(
                "repos:\n  - org: a\n    repo: b\n    template: true\n  - org: c\n    repo: d\n    template: true\n"
            ),
            2,
        )


class RescoreTest(unittest.TestCase):
    def test_rescoring_reads_a_snapshot_and_writes_one_without_collecting(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        out = directory / "metrics.json"
        with mock.patch.object(collect_metrics, "UrllibTransport", side_effect=AssertionError("a request was made")):
            status = collect_metrics.main(["--rescore", str(FIXTURES / "snapshot.json"), "--out", str(out)])
        self.assertEqual(status, 0)
        rescored = snap.read(out)
        self.assertEqual(list(rescored["packages"]), list(snap.read(FIXTURES / "snapshot.json")["packages"]))


class RenderCliTest(unittest.TestCase):
    def test_rendering_without_a_snapshot_says_which_task_to_run(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        status = render_dashboard.main(["--snapshot", str(directory / "missing.json"), "--out", str(directory)])
        self.assertEqual(status, 1)

    def test_local_rendering_produces_one_file_that_carries_the_reading(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        status = render_dashboard.main(["--snapshot", str(FIXTURES / "snapshot.json"), "--out", str(directory)])
        self.assertEqual(status, 0)
        self.assertEqual([path.name for path in directory.iterdir()], ["index.html"])
        page = (directory / "index.html").read_text()
        self.assertIn("tidyverse/tibble", page)

    def test_publishing_produces_the_document_beside_the_page(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        status = render_dashboard.main(
            ["--snapshot", str(FIXTURES / "snapshot_mirrors.json"), "--out", str(directory), "--publish"]
        )
        self.assertEqual(status, 0)
        published = json.loads((directory / "metrics.json").read_text())
        self.assertNotIn("workspace", published["packages"]["tidyverse/tibble"])
        self.assertTrue((directory / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
