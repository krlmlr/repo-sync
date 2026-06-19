#!/usr/bin/env python3
"""Discover the subset of repos.yml that is checked out locally.

Supports two layouts under a base directory:

  * flat siblings: ``<base>/<repo>`` (e.g. an active session where repos sit
    next to repo-sync, with no ``<org>/`` directory)
  * mirrors:       ``<base>/mirrors/<org>/<repo>`` (as produced by clone.sh)

A candidate directory matches an inventory entry only when its basename equals
the entry's ``repo`` AND its git ``origin`` remote resolves to ``<org>/<repo>``.
Matching is read-only and report-and-continue: unrecognized directories and a
missing local template are reported but do not stop discovery. The matched
subset is printed to stdout as JSON for the downstream reconcile engine.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
REPOS_YML = REPO_ROOT / "repos.yml"


def load_inventory(path: Path) -> tuple[list[dict], tuple[str, str] | None]:
    """Load repos.yml and return (entries, template_slug).

    Exits non-zero unless exactly one entry is flagged ``template: true``.
    """
    data = yaml.safe_load(path.read_text()) or {}
    entries = data.get("repos", [])
    flagged = [
        (e["org"], e["repo"]) for e in entries if e.get("template") is True
    ]
    if len(flagged) != 1:
        print(
            f"error: {path.name} has {len(flagged)} entries with template: true; "
            "expected exactly 1",
            file=sys.stderr,
        )
        sys.exit(2)
    return entries, flagged[0]


def resolve_origin(directory: Path) -> tuple[str, str] | None:
    """Return (org, repo) from the directory's git ``origin`` remote.

    Handles SSH (``git@host:org/repo.git``), HTTPS, and proxied URLs by taking
    the final two path segments and stripping a trailing ``.git``. Returns None
    when the directory is not a git repo or has no ``origin`` remote.
    """
    result = subprocess.run(
        ["git", "-C", str(directory), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if not url:
        return None
    tail = url.split(":")[-1] if ":" in url and "//" not in url.split(":")[-1] else url
    # Normalize both ':' (SSH) and '/' separators by splitting on both.
    parts = [p for p in tail.replace(":", "/").split("/") if p]
    if len(parts) < 2:
        return None
    org, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    return org, repo


def candidate_dirs(base: Path) -> list[Path]:
    """Yield candidate directories under base in both supported layouts."""
    candidates: list[Path] = []
    if base.is_dir():
        for child in sorted(base.iterdir()):
            if child.is_dir() and child.name != "mirrors":
                candidates.append(child)
    mirrors = base / "mirrors"
    if mirrors.is_dir():
        for org_dir in sorted(mirrors.iterdir()):
            if org_dir.is_dir():
                for repo_dir in sorted(org_dir.iterdir()):
                    if repo_dir.is_dir():
                        candidates.append(repo_dir)
    return candidates


def discover(base: Path, entries: list[dict], template_slug: tuple[str, str]):
    by_slug = {(e["org"].lower(), e["repo"].lower()): e for e in entries}

    matched: dict[tuple[str, str], dict] = {}
    extras: list[str] = []
    mismatches: list[str] = []

    for directory in candidate_dirs(base):
        origin = resolve_origin(directory)
        if origin is None:
            extras.append(f"{directory} (no origin remote)")
            continue
        slug = (origin[0].lower(), origin[1].lower())
        entry = by_slug.get(slug)
        basename = directory.name
        if entry is None:
            extras.append(f"{directory} (origin {origin[0]}/{origin[1]} not in inventory)")
            continue
        if basename.lower() != entry["repo"].lower():
            mismatches.append(
                f"{directory} (basename '{basename}' != repo '{entry['repo']}' "
                f"for origin {origin[0]}/{origin[1]})"
            )
            continue
        is_template = (entry["org"], entry["repo"]) == template_slug
        matched[(entry["org"], entry["repo"])] = {
            "org": entry["org"],
            "repo": entry["repo"],
            "path": str(directory.resolve()),
            "template": is_template,
        }

    return matched, extras, mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        type=Path,
        default=REPO_ROOT.parent,
        help="Directory to scan for checkouts (default: repo-sync's parent).",
    )
    args = parser.parse_args()

    entries, template_slug = load_inventory(REPOS_YML)
    matched, extras, mismatches = discover(args.base, entries, template_slug)

    for extra in extras:
        print(f"note: ignoring unrecognized directory: {extra}", file=sys.stderr)
    for mismatch in mismatches:
        print(f"note: skipping origin/basename mismatch: {mismatch}", file=sys.stderr)

    if not any(m["template"] for m in matched.values()):
        print(
            f"warning: template {template_slug[0]}/{template_slug[1]} is not "
            "checked out locally",
            file=sys.stderr,
        )

    subset = sorted(
        matched.values(), key=lambda m: (m["org"].lower(), m["repo"].lower())
    )
    print(json.dumps(subset, indent=2))

    print(
        f"discovered {len(subset)} repo(s) under {args.base}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
