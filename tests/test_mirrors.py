"""The mirror-derived groups, against real git repositories built for each test.

There are no mirrors in a test environment and there is no need for any: what the collector does on
the mirror path is run git in a directory, so a handful of small repositories built in a temporary
directory exercises the same code the forty-six real ones would.
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio.mirrors import (
    GitRunner,
    MirrorWriteAttempt,
    mirrors_present,
    template_group,
    workspace_group,
)

ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="Fixture",
    GIT_AUTHOR_EMAIL="fixture@example.invalid",
    GIT_COMMITTER_NAME="Fixture",
    GIT_COMMITTER_EMAIL="fixture@example.invalid",
    GIT_CONFIG_GLOBAL="/dev/null",
    GIT_CONFIG_SYSTEM="/dev/null",
)


def git(repo: Path, *args: str, date: str | None = None, check: bool = True) -> str:
    env = dict(ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {result.stderr}")
    return result.stdout


def commit(repo: Path, name: str, content: str, subject: str, date: str) -> None:
    (repo / name).write_text(content)
    git(repo, "add", name)
    git(repo, "commit", "-m", subject, date=date)


def build(root: Path) -> Path:
    """A mirrors directory: a bare template, and mirrors in three states against it."""
    mirrors = root / "mirrors"
    template = mirrors / "tpl" / "template"
    template.mkdir(parents=True)
    git(template, "init", "-b", "main")
    commit(template, "shared.txt", "one\n", "feat: template one", "2026-01-01T00:00:00Z")
    commit(template, "second.txt", "two\n", "feat: template two", "2026-02-01T00:00:00Z")
    commit(template, "third.txt", "three\n", "ci: template three", "2026-03-01T00:00:00Z")
    subprocess.run(
        ["git", "clone", "--mirror", str(template), str(mirrors / "tpl" / "template.git")],
        capture_output=True,
        text=True,
        env=ENV,
        check=True,
    )

    for slug in ("org/behind", "org/instep", "org/dirty"):
        mirror = mirrors / slug
        mirror.mkdir(parents=True)
        git(mirror, "init", "-b", "main")
        commit(mirror, "own.txt", "own\n", "chore: the package's own work", "2025-06-01T00:00:00Z")
        git(mirror, "remote", "add", "template", "../../tpl/template.git")
        git(mirror, "fetch", "--no-tags", "template")

    behind = mirrors / "org" / "behind"
    # Cherry-picked, then amended to a different subject: the same patch under another name.
    picks = git(behind, "log", "--reverse", "--format=%H", "template/main").split()
    git(behind, "cherry-pick", picks[1])
    git(behind, "commit", "--amend", "-m", "chore: adopt the second template change")

    instep = mirrors / "org" / "instep"
    for pick in git(instep, "log", "--reverse", "--format=%H", "template/main").split():
        git(instep, "cherry-pick", pick)

    dirty = mirrors / "org" / "dirty"
    (dirty / "own.txt").write_text("own, edited\n")
    (dirty / "staged.txt").write_text("staged\n")
    git(dirty, "add", "staged.txt")
    # A cherry-pick that stops on a conflict, which is the state a reconcile leaves behind.
    (dirty / "shared.txt").write_text("conflicting\n")
    git(dirty, "add", "shared.txt")
    git(dirty, "commit", "-m", "chore: conflict with the template", date="2026-06-01T00:00:00Z")
    first = git(dirty, "log", "--reverse", "--format=%H", "template/main").split()[0]
    git(dirty, "cherry-pick", first, check=False)
    return mirrors


class MirrorsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.mirrors = build(self.root)
        self.runner = GitRunner()
        self.bare = self.mirrors / "tpl" / "template.git"

    def test_mirrors_are_detected_by_the_directory(self):
        self.assertTrue(mirrors_present(self.mirrors))
        self.assertFalse(mirrors_present(self.root / "absent"))

    def test_a_cherry_picked_commit_is_present_even_with_a_rewritten_subject(self):
        group = template_group(self.runner, self.mirrors / "org" / "behind", self.bare)
        self.assertTrue(group["collected"])
        self.assertEqual(group["outstanding"], 2)
        subjects = [commit["subject"] for commit in group["outstanding_commits"]]
        self.assertEqual(subjects, ["feat: template one", "ci: template three"])

    def test_bounding_does_not_change_the_result(self):
        mirror = self.mirrors / "org" / "behind"
        bounded = template_group(self.runner, mirror, self.bare, bounded=True)
        unbounded = template_group(self.runner, mirror, self.bare, bounded=False)
        self.assertIsNotNone(bounded["bounded_from"])
        self.assertIsNone(unbounded["bounded_from"])
        self.assertEqual(bounded["outstanding_commits"], unbounded["outstanding_commits"])

    def test_the_oldest_outstanding_commit_is_dated(self):
        group = template_group(self.runner, self.mirrors / "org" / "behind", self.bare)
        self.assertEqual(group["oldest_outstanding_at"], "2026-01-01T00:00:00Z")

    def test_a_mirror_in_step_records_none_and_no_date(self):
        group = template_group(self.runner, self.mirrors / "org" / "instep", self.bare)
        self.assertEqual(group["outstanding"], 0)
        self.assertEqual(group["outstanding_commits"], [])
        self.assertIsNone(group["oldest_outstanding_at"])

    def test_a_mirror_without_the_template_remote_is_uncollected(self):
        plain = self.root / "plain"
        plain.mkdir()
        git(plain, "init", "-b", "main")
        commit(plain, "a.txt", "a\n", "chore: alone", "2026-01-01T00:00:00Z")
        group = template_group(self.runner, plain, self.bare)
        self.assertFalse(group["collected"])
        self.assertIn("template", group["reason"])

    def test_a_stopped_cherry_pick_with_staged_and_unstaged_changes(self):
        group = workspace_group(self.runner, self.mirrors / "org" / "dirty")
        self.assertTrue(group["dirty"])
        self.assertGreaterEqual(group["staged"], 1)
        self.assertGreaterEqual(group["unstaged"], 1)
        self.assertIn("cherry_pick", group["operation_in_progress"] or [])

    def test_unpushed_commits_are_counted_against_the_upstream(self):
        mirror = self.mirrors / "org" / "instep"
        remote = self.root / "upstream.git"
        subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], env=ENV, check=True)
        git(mirror, "remote", "add", "origin", str(remote))
        git(mirror, "push", "--quiet", "--set-upstream", "origin", "main")
        commit(mirror, "later.txt", "later\n", "chore: not pushed yet", "2026-07-01T00:00:00Z")
        group = workspace_group(self.runner, mirror)
        self.assertEqual(group["unpushed"], 1)
        self.assertEqual(group["upstream"], "origin/main")

    def test_a_clean_mirror_says_so(self):
        group = workspace_group(self.runner, self.mirrors / "org" / "instep")
        self.assertFalse(group["dirty"])
        self.assertIsNone(group["operation_in_progress"])

    def test_a_write_subcommand_is_refused_before_it_runs(self):
        for args in (["commit", "-m", "no"], ["checkout", "main"], ["fetch"], ["reset", "--hard"]):
            with self.subTest(command=args[0]):
                with self.assertRaises(MirrorWriteAttempt):
                    self.runner.run(self.mirrors / "org" / "instep", args)

    def test_collection_leaves_every_mirror_byte_for_byte_as_it_found_it(self):
        def fingerprint(path: Path) -> dict[str, tuple[int, float]]:
            return {
                str(item.relative_to(path)): (item.stat().st_size, item.stat().st_mtime)
                for item in sorted(path.rglob("*"))
                if item.is_file()
            }

        before = {slug: fingerprint(self.mirrors / slug) for slug in ("org/behind", "org/instep", "org/dirty")}
        for slug in ("org/behind", "org/instep", "org/dirty"):
            template_group(self.runner, self.mirrors / slug, self.bare)
            workspace_group(self.runner, self.mirrors / slug)
        after = {slug: fingerprint(self.mirrors / slug) for slug in ("org/behind", "org/instep", "org/dirty")}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
