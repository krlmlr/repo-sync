#!/usr/bin/env python3
"""Fetch branch list from krlmlr/actions-sync and write repos.yml."""

import subprocess
import sys
from pathlib import Path

import yaml

REMOTE = "https://github.com/krlmlr/actions-sync"
REPO_ROOT = Path(__file__).parent.parent
REPOS_YML = REPO_ROOT / "repos.yml"
ENTRY_KEYS = ("org", "repo", "maintained", "template")


def fetch_branches(remote: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-remote", "--heads", remote],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"error: git ls-remote failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    branches = []
    for line in result.stdout.splitlines():
        ref = line.split("\t", 1)[1]  # e.g. refs/heads/org/repo
        branches.append(ref.removeprefix("refs/heads/"))
    return branches


def parse_repos(branches: list[str]) -> list[dict]:
    repos = []
    for name in branches:
        if "/" not in name:
            continue
        org, repo = name.split("/", 1)
        repos.append({"org": org, "repo": repo})
    if not repos:
        print("error: no org/repo branches found — refusing to write empty inventory", file=sys.stderr)
        sys.exit(1)
    return sorted(repos, key=lambda e: (e["org"].lower(), e["repo"].lower()))


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("repos", [])


def load_template_flags(existing: list[dict], path: Path) -> set[tuple[str, str]]:
    flagged = [
        (e["org"], e["repo"])
        for e in existing
        if e.get("template") is True
    ]
    if len(flagged) > 1:
        print(
            f"error: existing {path.name} has {len(flagged)} entries with template: true; expected at most 1: {flagged}",
            file=sys.stderr,
        )
        sys.exit(1)
    return set(flagged)


def apply_template_flags(repos: list[dict], flagged: set[tuple[str, str]]) -> None:
    inventory = {(e["org"], e["repo"]) for e in repos}
    missing = flagged - inventory
    if missing:
        print(
            f"error: previously-flagged template entr{'y' if len(missing) == 1 else 'ies'} not in new branch list: {sorted(missing)}",
            file=sys.stderr,
        )
        print("hint: pick a new template explicitly before re-running", file=sys.stderr)
        sys.exit(1)
    for entry in repos:
        if (entry["org"], entry["repo"]) in flagged:
            entry["template"] = True


def load_maintained_flags(existing: list[dict]) -> set[tuple[str, str]]:
    return {(e["org"], e["repo"]) for e in existing if e.get("maintained") is True}


def apply_maintained_flags(repos: list[dict], flagged: set[tuple[str, str]]) -> None:
    # Unlike the template, nothing depends on any particular entry being maintained,
    # so a flagged repo that has left the branch list is reported and dropped rather than fatal:
    # the diff shows the entry going, and reviewing that diff is the gate.
    inventory = {(e["org"], e["repo"]) for e in repos}
    missing = flagged - inventory
    if missing:
        print(
            f"note: dropping maintained entr{'y' if len(missing) == 1 else 'ies'} not in new branch list: {sorted(missing)}",
            file=sys.stderr,
        )
    for entry in repos:
        if (entry["org"], entry["repo"]) in flagged:
            entry["maintained"] = True


def main() -> None:
    existing = load_existing(REPOS_YML)
    flagged = load_template_flags(existing, REPOS_YML)
    maintained = load_maintained_flags(existing)
    branches = fetch_branches(REMOTE)
    repos = parse_repos(branches)
    apply_template_flags(repos, flagged)
    apply_maintained_flags(repos, maintained)
    # `org` and `repo` first, then the flags, rather than yaml's alphabetical order,
    # which would put `maintained` ahead of the name it qualifies.
    repos = [{k: e[k] for k in ENTRY_KEYS if k in e} for e in repos]
    content = yaml.dump({"repos": repos}, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp = REPOS_YML.with_suffix(".yml.tmp")
    tmp.write_text(content)
    tmp.replace(REPOS_YML)
    print(f"wrote {len(repos)} repos to {REPOS_YML}")


if __name__ == "__main__":
    main()
