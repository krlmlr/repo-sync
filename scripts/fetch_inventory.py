#!/usr/bin/env python3
"""Fetch branch list from krlmlr/actions-sync and write repos.yml."""

import subprocess
import sys
from pathlib import Path

import yaml

REMOTE = "https://github.com/krlmlr/actions-sync"
REPO_ROOT = Path(__file__).parent.parent
REPOS_YML = REPO_ROOT / "repos.yml"


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


def main() -> None:
    branches = fetch_branches(REMOTE)
    repos = parse_repos(branches)
    REPOS_YML.write_text(yaml.dump({"repos": repos}, default_flow_style=False, allow_unicode=True))
    print(f"wrote {len(repos)} repos to {REPOS_YML}")


if __name__ == "__main__":
    main()
