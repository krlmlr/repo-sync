#!/usr/bin/env python3
"""Render a collected snapshot as the status page.

Takes a snapshot and produces a page; collects nothing, and needs no network to do it.

Locally that is one file with the reading inlined, which opens from disk on a double-click.
For publication it is two -- a page that fetches `metrics.json`, and the `metrics.json` it fetches,
with the workspace group removed and the reading retained as history.

Usage:
    python3 scripts/render_dashboard.py [--snapshot reports/metrics.json] [--out reports]
    python3 scripts/render_dashboard.py --publish --out <worktree of the deploy branch>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio import snapshot as snap
from portfolio.render import write_local, write_published

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", type=Path, default=REPO_ROOT / "reports" / "metrics.json")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "reports")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="write the published shape: page, document, retained snapshot and history series",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot = snap.read(args.snapshot)
    if snapshot is None:
        print(
            f"FAIL: no snapshot at {args.snapshot} -- run `mise run metrics` first",
            file=sys.stderr,
        )
        return 1

    if args.publish:
        written = write_published(snapshot, args.out)
        for path in written:
            print(f"wrote {path}")
        return 0

    page = write_local(snapshot, args.out)
    print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
