"""What only a machine holding `mirrors/` can say.

Two groups come from here. The template position -- which template commits have no equivalent in a
mirror -- is the one metric no API can compute, because answering it needs both histories. The
workspace group -- dirty tree, unpushed commits, an interrupted operation -- is the one metric that
is about the laptop rather than about the package, which is why publication strips it by name.

Equivalence is patch identity, not commit identity: template changes arrive by cherry-pick, so the
mirrors and the template share no history and "behind by N" describes nothing. The mirror side is
bounded by date -- a commit authored before the oldest template commit cannot be a copy of one --
which is what keeps patch-ids over two full histories from being paid forty-six times.

Every git command here is read-only, and the allowlist below is the mechanism rather than the
intention: collection runs against a working tree someone is in the middle of using, and a tool
that refreshes an index or moves a HEAD while they work is a tool that eats their afternoon.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Subcommands that read. `git status` is on it only because it is always run with
# `--no-optional-locks`, which is what stops it from refreshing the index it just read.
READ_ONLY_SUBCOMMANDS = frozenset(
    {
        "cat-file",
        "diff-tree",
        "for-each-ref",
        "log",
        "patch-id",
        "rev-list",
        "rev-parse",
        "show-ref",
        "status",
        "symbolic-ref",
    }
)


class MirrorWriteAttempt(AssertionError):
    """A git subcommand that is not on the allowlist, refused before it runs."""


@dataclass
class GitRunner:
    """Every git invocation on a mirror path, in one place that can be checked and stubbed."""

    def run(self, repo: Path, args: list[str], *, stdin: str | None = None, check: bool = False) -> str:
        if not args or args[0] not in READ_ONLY_SUBCOMMANDS:
            raise MirrorWriteAttempt(f"git {args[0] if args else ''} is not a read-only subcommand")
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            input=stdin,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} in {repo}: {result.stderr.strip()}")
        return result.stdout

    def patch_ids(self, repo: Path, rev_args: list[str]) -> dict[str, str]:
        """Patch identity to commit, for a revision range.

        `rev-list | diff-tree | patch-id` is what `git cherry` runs internally. It is spelled out
        here because `git cherry`'s `<limit>` argument bounds the side being *reported* -- the
        template -- and the side that needs bounding is the mirror's history.
        """
        revs = self.run(repo, ["rev-list", "--no-merges", *rev_args])
        if not revs.strip():
            return {}
        patches = self.run(repo, ["diff-tree", "--stdin", "-p", "--root"], stdin=revs)
        ids = self.run(repo, ["patch-id", "--stable"], stdin=patches)
        mapping: dict[str, str] = {}
        for line in ids.splitlines():
            parts = line.split()
            if len(parts) == 2:
                mapping[parts[0]] = parts[1]
        return mapping


def mirrors_present(mirrors_dir: Path) -> bool:
    return mirrors_dir.is_dir()


def template_ref(runner: GitRunner, mirror: Path, bare_dir: Path) -> str | None:
    """The ref in the mirror that holds the template's default branch.

    The branch name comes from the bare mirror the `template` remote points at, rather than from a
    guess at `main`: it is the repository that knows, and it is on disk beside the mirrors.
    """
    branch = runner.run(bare_dir, ["symbolic-ref", "--short", "HEAD"]).strip() if bare_dir.is_dir() else ""
    candidates = [f"template/{branch}"] if branch else []
    candidates += ["template/main", "template/master"]
    for candidate in candidates:
        if runner.run(mirror, ["rev-parse", "--verify", "--quiet", f"refs/remotes/{candidate}"]).strip():
            return candidate
    return None


def template_group(
    runner: GitRunner,
    mirror: Path,
    bare_dir: Path,
    *,
    bounded: bool = True,
) -> dict[str, Any]:
    """Which template commits have no equivalent in this mirror, and how old the oldest is."""
    ref = template_ref(runner, mirror, bare_dir)
    if ref is None:
        return {
            "collected": False,
            "reason": "no `template` remote in this mirror -- run `mise run clone`",
        }

    template_patches = runner.patch_ids(mirror, [ref])
    if not template_patches:
        return {"collected": False, "reason": f"no commits on {ref}"}

    oldest = runner.run(mirror, ["log", "--reverse", "--format=%H %aI", "--no-merges", ref]).splitlines()
    bound = oldest[0].split()[1] if oldest and bounded else None
    mirror_args = ["HEAD"] + ([f"--since={bound}"] if bound else [])
    mirror_patches = set(runner.patch_ids(mirror, mirror_args))

    outstanding = []
    for patch_id, commit in template_patches.items():
        if patch_id in mirror_patches:
            continue
        line = runner.run(mirror, ["log", "-1", "--format=%H%x09%aI%x09%s", commit]).strip()
        sha, _, rest = line.partition("\t")
        authored, _, subject = rest.partition("\t")
        outstanding.append({"sha": sha, "authored_at": authored, "subject": subject})
    outstanding.sort(key=lambda commit: commit["authored_at"])

    return {
        "collected": True,
        "template_ref": ref,
        "bounded_from": bound,
        "outstanding": len(outstanding),
        # Enough to name the work without carrying a whole history into the document.
        "outstanding_commits": outstanding[:20],
        "oldest_outstanding_at": outstanding[0]["authored_at"] if outstanding else None,
    }


def workspace_group(runner: GitRunner, mirror: Path) -> dict[str, Any]:
    """The state of the working copy: dirty, ahead, or stopped in the middle of something."""
    porcelain = runner.run(mirror, ["status", "--porcelain"]).splitlines()
    staged = sum(1 for line in porcelain if line[:1] not in (" ", "?", ""))
    unstaged = sum(1 for line in porcelain if line[1:2] not in (" ", "") and line[:1] != "?")
    untracked = sum(1 for line in porcelain if line.startswith("??"))

    upstream = runner.run(mirror, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]).strip()
    unpushed = None
    if upstream:
        count = runner.run(mirror, ["rev-list", "--count", f"{upstream}..HEAD"]).strip()
        unpushed = int(count) if count.isdigit() else None

    git_dir = mirror / ".git"
    operations = {
        "rebase": (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists(),
        "merge": (git_dir / "MERGE_HEAD").exists(),
        "cherry_pick": (git_dir / "CHERRY_PICK_HEAD").exists(),
        "revert": (git_dir / "REVERT_HEAD").exists(),
        "bisect": (git_dir / "BISECT_LOG").exists(),
    }
    return {
        "dirty": bool(porcelain),
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "unpushed": unpushed,
        "upstream": upstream or None,
        "operation_in_progress": [name for name, active in operations.items() if active] or None,
    }
