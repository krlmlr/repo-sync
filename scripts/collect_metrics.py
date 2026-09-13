#!/usr/bin/env python3
"""Collect one snapshot of the portfolio: GitHub, CRAN, and the mirrors when they are here.

Off the critical path by construction: nothing in `clone` or `sync` imports this, and a run that
fails leaves a stale page rather than an unmirrored portfolio.

A credential is required and a stored secret is not. GitHub's GraphQL API refuses anonymous
requests outright, and batching is what makes reading forty-six repositories cheap, so there is no
anonymous mode to fall back to. In Actions the credential is the `GITHUB_TOKEN` minted for this
repository; locally it is an existing `gh` login, read at run time. Neither is a secret this
project keeps, rotates, or can leak.

Usage:
    python3 scripts/collect_metrics.py [--out reports/metrics.json] [--no-cran]
    python3 scripts/collect_metrics.py --rescore reports/metrics.json
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio import snapshot as snap
from portfolio.collect import collect, report
from portfolio.config import load_config
from portfolio.cran import CranSource
from portfolio.github import GitHubSource
from portfolio.inventory import InventoryError, load_inventory
from portfolio.score import score_snapshot
from portfolio.transport import Client, UrllibTransport

REPO_ROOT = Path(__file__).resolve().parent.parent


class MissingCredential(Exception):
    """No credential, said once and with both ways of providing one named."""


def resolve_token(environ: dict[str, str] | None = None) -> str:
    """The token from the environment, or from an existing `gh` login, or a message saying so."""
    environ = os.environ if environ is None else environ
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = environ.get(name)
        if token:
            return token
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    raise MissingCredential(
        "no GitHub credential: set GITHUB_TOKEN (Actions mints one) or run `gh auth login`. "
        "GitHub's GraphQL API refuses anonymous requests, so there is nothing to collect without one."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos", type=Path, default=REPO_ROOT / "repos.yml")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "dashboard.yml")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "reports" / "metrics.json")
    parser.add_argument("--previous", type=Path, default=None, help="snapshot to carry values forward from")
    parser.add_argument("--mirrors", type=Path, default=REPO_ROOT / "mirrors")
    parser.add_argument("--no-cran", action="store_true", help="skip CRAN entirely")
    parser.add_argument(
        "--rescore",
        type=Path,
        default=None,
        help="recompute the scores of an existing snapshot with the current weights, collecting nothing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    now = datetime.now(timezone.utc)

    if args.rescore is not None:
        existing = snap.read(args.rescore)
        if existing is None:
            print(f"FAIL: no snapshot to rescore at {args.rescore}", file=sys.stderr)
            return 1
        snap.write(score_snapshot(existing, config=config, now=now), args.out)
        print(f"rescored {len(existing.get('packages', {}))} packages into {args.out}")
        return 0

    try:
        inventory = load_inventory(args.repos)
    except InventoryError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    try:
        token = resolve_token()
    except MissingCredential as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    client = Client(transport=UrllibTransport())
    github = GitHubSource(client, token, config, now=now)
    cran = None if args.no_cran else CranSource(client)
    previous = snap.read(args.previous if args.previous else args.out)

    result = collect(
        inventory=inventory,
        config=config,
        github=github,
        cran=cran,
        mirrors_dir=args.mirrors,
        previous=previous,
        now=now,
    )
    snap.write(result, args.out)
    print(f"wrote {len(result['packages'])} packages to {args.out}")
    return report(result)


if __name__ == "__main__":
    sys.exit(main())
