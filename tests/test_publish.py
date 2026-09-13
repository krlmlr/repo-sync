"""Publication, against a throwaway remote rather than against the real deploy branch.

Everything the script does to the deploy branch -- creating it when it is absent, committing only
when the reading changed, retaining each snapshot and appending to the series -- is a git operation,
so a bare repository in a temporary directory exercises all of it.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio import snapshot as snap

from tests.support import FIXTURES
from tests.test_mirrors import ENV

ROOT = Path(__file__).resolve().parents[1]


def publish(*, snapshot: Path, workdir: Path, branch: str = "gh-pages") -> subprocess.CompletedProcess:
    env = dict(
        ENV,
        REPO_SYNC_SNAPSHOT=str(snapshot),
        REPO_SYNC_PUBLISH_WORKDIR=str(workdir),
        REPO_SYNC_PUBLISH_BRANCH=branch,
    )
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "publish_dashboard.sh")], capture_output=True, text=True, env=env
    )


def branch_files(remote: Path, branch: str = "gh-pages") -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(remote), "ls-tree", "-r", "--name-only", branch],
        capture_output=True,
        text=True,
        env=ENV,
    )
    return sorted(listing.stdout.split())


def file_on_branch(remote: Path, path: str, branch: str = "gh-pages") -> str:
    return subprocess.run(
        ["git", "-C", str(remote), "show", f"{branch}:{path}"], capture_output=True, text=True, env=ENV
    ).stdout


def commit_count(remote: Path, branch: str = "gh-pages") -> int:
    result = subprocess.run(
        ["git", "-C", str(remote), "rev-list", "--count", branch], capture_output=True, text=True, env=ENV
    )
    return int(result.stdout.strip() or 0)


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.remote = self.directory / "remote.git"
        subprocess.run(["git", "init", "--quiet", "--bare", str(self.remote)], env=ENV, check=True)
        # A stand-in for this repository: a checkout with a remote, which is all the script needs.
        self.workdir = self.directory / "checkout"
        self.workdir.mkdir()
        subprocess.run(["git", "init", "--quiet", "-b", "main", str(self.workdir)], env=ENV, check=True)
        subprocess.run(
            ["git", "-C", str(self.workdir), "commit", "--quiet", "--allow-empty", "-m", "init"], env=ENV, check=True
        )
        subprocess.run(
            ["git", "-C", str(self.workdir), "remote", "add", "origin", str(self.remote)], env=ENV, check=True
        )

    def test_a_first_run_establishes_the_branch(self):
        result = publish(snapshot=FIXTURES / "snapshot_mirrors.json", workdir=self.workdir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("creating it", result.stdout)
        files = branch_files(self.remote)
        self.assertIn("index.html", files)
        self.assertIn("metrics.json", files)
        self.assertIn("history.jsonl", files)
        self.assertEqual(len([name for name in files if name.startswith("history/")]), 1)

    def test_the_published_snapshot_carries_no_workspace_group(self):
        publish(snapshot=FIXTURES / "snapshot_mirrors.json", workdir=self.workdir)
        published = json.loads(file_on_branch(self.remote, "metrics.json"))
        self.assertNotIn("workspace", published["groups"])
        for entry in published["packages"].values():
            self.assertNotIn("workspace", entry)
        self.assertNotIn("workspace", file_on_branch(self.remote, "metrics.json"))
        # The template group is public either way, and stays.
        self.assertTrue(published["packages"]["tidyverse/tibble"]["template"]["collected"])

    def test_an_unchanged_reading_adds_no_commit(self):
        publish(snapshot=FIXTURES / "snapshot_mirrors.json", workdir=self.workdir)
        before = commit_count(self.remote)
        again = publish(snapshot=FIXTURES / "snapshot_mirrors.json", workdir=self.workdir)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("nothing to publish", again.stdout)
        self.assertEqual(commit_count(self.remote), before)

    def test_two_readings_leave_two_retained_snapshots_and_two_series_entries(self):
        publish(snapshot=FIXTURES / "snapshot_mirrors.json", workdir=self.workdir)

        later = snap.read(FIXTURES / "snapshot_mirrors.json")
        later["collected_at"] = "2026-09-02T12:00:00Z"
        later["portfolio"]["collected_at"] = "2026-09-02T12:00:00Z"
        second = self.directory / "later.json"
        snap.write(later, second)
        result = publish(snapshot=second, workdir=self.workdir)
        self.assertEqual(result.returncode, 0, result.stderr)

        retained = [name for name in branch_files(self.remote) if name.startswith("history/")]
        self.assertEqual(len(retained), 2)
        series = [json.loads(line) for line in file_on_branch(self.remote, "history.jsonl").splitlines() if line.strip()]
        self.assertEqual([point["collected_at"] for point in series], ["2026-09-01T12:00:00Z", "2026-09-02T12:00:00Z"])
        self.assertEqual(commit_count(self.remote), 2)

    def test_without_a_snapshot_it_says_which_task_to_run(self):
        result = publish(snapshot=self.directory / "absent.json", workdir=self.workdir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("mise run metrics", result.stderr)

    def test_publication_touches_nothing_in_the_working_repository(self):
        before = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True
        ).stdout
        publish(snapshot=FIXTURES / "snapshot.json", workdir=self.workdir)
        after = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True
        ).stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
