#!/usr/bin/env python3
"""Fetch branch list from krlmlr/actions-sync and write repos.yml."""

import json
import subprocess
import sys
from pathlib import Path

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


def load_template_flags(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    result = subprocess.run(
        ["yq", ".repos[] | select(.template == true) | [.org, .repo]"],
        input=path.read_text(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"error: yq failed reading {path.name}:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    flagged = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Parse JSON array output from yq
        try:
            org, repo = json.loads(line)
            flagged.append((org, repo))
        except (json.JSONDecodeError, ValueError):
            pass
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


def write_repos_with_yq(path: Path, repos: list[dict]) -> None:
    """Write repos to YAML using yq for consistent formatting."""
    data = {"repos": repos}
    json_input = json.dumps(data)
    result = subprocess.run(
        ["yq", "-y", "."],
        input=json_input,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"error: yq failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Write atomically
    tmp = path.with_suffix(".yml.tmp")
    tmp.write_text(result.stdout)
    tmp.replace(path)


def main() -> None:
    flagged = load_template_flags(REPOS_YML)
    branches = fetch_branches(REMOTE)
    repos = parse_repos(branches)
    apply_template_flags(repos, flagged)
    write_repos_with_yq(REPOS_YML, repos)
    print(f"wrote {len(repos)} repos to {REPOS_YML}")


if __name__ == "__main__":
    main()
