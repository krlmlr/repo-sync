#!/usr/bin/env python3
"""Build the committed fixture snapshots the renderer tests run against.

They are generated rather than hand-written so that they are snapshots the collector actually
produces -- a hand-made fixture drifts from the schema the moment a field is added, and then the
page is tested against a document nothing writes.

Every shape the renderer has to handle is represented: fresh, stale, never observed, not an R
package, no CI, no releases, archived, dormant, a CRAN deadline, and a reading taken where the
mirrors are not.

Run `python3 tests/make_fixtures.py` after changing the schema; `tests/test_fixtures.py` fails
when the committed files no longer match what this produces.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from portfolio import snapshot as snap
from portfolio.collect import collect
from portfolio.config import Config
from portfolio.cran import CranSource
from portfolio.github import GitHubSource
from portfolio.inventory import load_inventory
from portfolio.score import score_snapshot
from portfolio.transport import Client
from tests.support import FIXTURES, NOW, FakeTransport, ago, check_page, issue, pull_request, repository, run

INVENTORY = {
    "repos": [
        {"org": "cynkra", "repo": "cynkratemplate", "template": True},
        {"org": "ghost", "repo": "missing"},
        {"org": "ghost", "repo": "never"},
        {"org": "krlmlr", "repo": "bindr"},
        {"org": "krlmlr", "repo": "notapackage"},
        {"org": "r-dbi", "repo": "RKazam"},
        {"org": "tidyverse", "repo": "tibble"},
    ]
}


def description(package: str, version: str) -> str:
    return f"Package: {package}\nVersion: {version}\nTitle: A fixture package\n"


def cran_description(package: str, version: str, published: str) -> str:
    return f"Package: {package}\nVersion: {version}\nDate/Publication: {published} 09:20:02 UTC\n"


def repositories() -> dict[str, dict]:
    return {
        "cynkra/cynkratemplate": repository(
            "cynkra/cynkratemplate",
            description_file=description("cynkratemplate", "0.1.0.9000"),
            permission="ADMIN",
            releases=[{"tagName": "v0.1.0", "url": "https://example.invalid/r", "publishedAt": ago(40), "isDraft": False}],
            commits=[(ago(5), "chore: bump the template"), (ago(3), "docs: explain the hook")],
            commits_recent=2,
            authors=["krlmlr"],
            last_commit=ago(3),
        ),
        # Readable in the previous reading and gone in this one: the stale row.
        "ghost/missing": repository(
            "ghost/missing",
            description_file=description("ghostly", "1.0.0"),
            releases=[{"tagName": "v1.0.0", "url": "https://example.invalid/g", "publishedAt": ago(200), "isDraft": False}],
            commits=[(ago(150), "fix: an old fix")],
            commits_recent=0,
            authors=["someone"],
            last_commit=ago(150),
        ),
        # Archived, dormant, clean on CRAN, and running no workflows at all.
        "krlmlr/bindr": repository(
            "krlmlr/bindr",
            description_file=description("bindr", "0.1.2"),
            archived=True,
            permission="ADMIN",
            releases=[{"tagName": "v0.1.2", "url": "https://example.invalid/b", "publishedAt": ago(1400), "isDraft": False}],
            commits=[],
            commits_recent=0,
            authors=[],
            last_commit=ago(1400),
        ),
        # Not an R package, never released, and with a tracker nobody has answered.
        "krlmlr/notapackage": repository(
            "krlmlr/notapackage",
            permission="ADMIN",
            releases=[],
            commits=[(ago(2), "feat: add a thing")],
            commits_recent=4,
            authors=["krlmlr", "someone"],
            last_commit=ago(2),
            issues=[issue(created=ago(120), updated=ago(115)), issue(created=ago(10), comments=["OWNER"])],
            pulls=[pull_request(created=ago(30), association="NONE")],
        ),
        # Red for a fortnight, under a CRAN deadline, with unreleased user-facing work.
        "r-dbi/RKazam": repository(
            "r-dbi/RKazam",
            description_file=description("RKazam", "0.2.0.9000"),
            releases=[{"tagName": "v0.2.0", "url": "https://example.invalid/k", "publishedAt": ago(90), "isDraft": False}],
            commits=[
                (ago(80), "feat: add the kazam"),
                (ago(60), "fix: stop the kazam leaking"),
                (ago(20), "chore: tidy up"),
                (ago(10), "an unconventional subject"),
            ],
            commits_recent=4,
            authors=["krlmlr", "someone", "another"],
            last_commit=ago(10),
            issues=[
                issue(created=ago(200), updated=ago(190)),
                issue(created=ago(100), updated=ago(95)),
                issue(created=ago(3), comments=["NONE"]),
            ],
            pulls=[
                pull_request(created=ago(40), association="NONE"),
                pull_request(created=ago(20), bot=True),
                pull_request(created=ago(2), draft=True),
            ],
        ),
        # The healthy case: green, released, answered, with a development version ahead of CRAN.
        "tidyverse/tibble": repository(
            "tidyverse/tibble",
            description_file=description("tibble", "3.3.1.9000"),
            permission="WRITE",
            releases=[
                {"tagName": "v3.3.2", "url": "https://example.invalid/t", "publishedAt": None, "createdAt": ago(1), "isDraft": True},
                {"tagName": "v3.3.1", "url": "https://example.invalid/t", "publishedAt": ago(30), "isDraft": False},
            ],
            commits=[(ago(20), "docs: clarify a vignette"), (ago(4), "chore: bump dev version")],
            commits_recent=6,
            authors=["krlmlr", "hadley"],
            last_commit=ago(4),
            issues=[issue(created=ago(20), comments=["MEMBER"]), issue(created=ago(400), comments=["NONE"] * 12, total=12)],
            pulls=[pull_request(created=ago(5), association="MEMBER", reviews=1, decision="APPROVED")],
        ),
    }


def runs() -> dict[str, list[dict]]:
    return {
        "cynkra/cynkratemplate": [run(conclusion="success", created=ago(day)) for day in (30, 20, 10, 2)],
        "ghost/missing": [run(conclusion="success", created=ago(60))],
        "krlmlr/bindr": [],
        "krlmlr/notapackage": [],
        # Alternating, and green at the end: flaky rather than broken.
        "r-dbi/RKazam": [
            run(conclusion="failure", created=ago(30), duration=900),
            run(conclusion="success", created=ago(25), duration=800),
            run(conclusion="failure", created=ago(14), duration=1000),
            run(conclusion="failure", created=ago(9), duration=1100),
            run(conclusion="failure", created=ago(1), duration=1200),
        ],
        "tidyverse/tibble": [
            run(conclusion="failure", created=ago(50), duration=700),
            run(conclusion="success", created=ago(40), duration=650),
            run(conclusion="cancelled", created=ago(30), duration=100),
            run(conclusion="success", created=ago(12), duration=600),
            run(conclusion="success", created=ago(3), duration=620),
        ],
    }


def cran() -> dict[str, tuple[str | None, str]]:
    return {
        "tibble": (check_page("tibble"), cran_description("tibble", "3.3.1", "2026-01-11")),
        "bindr": (check_page("here"), cran_description("bindr", "0.1.2", "2023-03-02")),
        "RKazam": (check_page("RKazam"), cran_description("RKazam", "0.2.0", "2026-06-03")),
        "ghostly": (None, cran_description("ghostly", "1.0.0", "2026-02-02")),
    }


def config() -> Config:
    # Three per query rather than ten, so a seven-entry fixture still exercises batching.
    return Config(collection=dict(Config().collection, graphql_batch=3))


def collect_fixture(*, missing: tuple[str, ...] = (), previous=None, cran_down: bool = False):
    inventory = load_inventory(FIXTURES / "repos.yml")
    available = {slug: node for slug, node in repositories().items() if slug not in missing}
    transport = FakeTransport(repos=available, runs=runs(), cran=cran(), cran_down=cran_down)
    client = Client(transport=transport, sleep=lambda _: None)
    settings = config()
    github = GitHubSource(client, "fixture-token", settings, now=NOW)
    return collect(
        inventory=inventory,
        config=settings,
        github=github,
        cran=CranSource(client),
        mirrors_dir=FIXTURES / "no-mirrors",
        previous=previous,
        now=NOW,
        log=lambda message: None,
    )


def with_mirror_groups(base: dict) -> dict:
    """The same reading as taken on a machine that has the mirrors.

    The groups are attached here rather than collected, because their shape is verified against
    real git repositories in `test_mirrors.py`; what the renderer needs from a fixture is a
    snapshot that carries them.
    """
    mirrored = deepcopy(base)
    mirrored["groups_collected"] = {"template": True, "workspace": True}
    outstanding = {
        "cynkra/cynkratemplate": {"collected": False, "reason": "the template is not measured against itself"},
        "ghost/missing": {"collected": False, "reason": "no mirror at mirrors/ghost/missing"},
        "ghost/never": {"collected": False, "reason": "no mirror at mirrors/ghost/never"},
        "krlmlr/bindr": {
            "collected": True,
            "template_ref": "template/main",
            "bounded_from": ago(700),
            "outstanding": 9,
            "outstanding_commits": [{"sha": "0" * 40, "authored_at": ago(400), "subject": "feat: template commit"}],
            "oldest_outstanding_at": ago(400),
        },
        "krlmlr/notapackage": {
            "collected": True,
            "template_ref": "template/main",
            "bounded_from": ago(700),
            "outstanding": 0,
            "outstanding_commits": [],
            "oldest_outstanding_at": None,
        },
        "r-dbi/RKazam": {
            "collected": True,
            "template_ref": "template/main",
            "bounded_from": ago(700),
            "outstanding": 3,
            "outstanding_commits": [{"sha": "1" * 40, "authored_at": ago(120), "subject": "ci: template commit"}],
            "oldest_outstanding_at": ago(120),
        },
        "tidyverse/tibble": {
            "collected": True,
            "template_ref": "template/main",
            "bounded_from": ago(700),
            "outstanding": 1,
            "outstanding_commits": [{"sha": "2" * 40, "authored_at": ago(30), "subject": "chore: template commit"}],
            "oldest_outstanding_at": ago(30),
        },
    }
    workspaces = {
        "r-dbi/RKazam": {
            "dirty": True,
            "staged": 1,
            "unstaged": 2,
            "untracked": 0,
            "unpushed": 3,
            "upstream": "origin/main",
            "operation_in_progress": ["cherry_pick"],
        }
    }
    for slug, entry in mirrored["packages"].items():
        entry["template"] = outstanding.get(slug, {"collected": False, "reason": f"no mirror at mirrors/{slug}"})
        entry["workspace"] = workspaces.get(
            slug,
            {
                "dirty": False,
                "staged": 0,
                "unstaged": 0,
                "untracked": 0,
                "unpushed": 0,
                "upstream": "origin/main",
                "operation_in_progress": None,
            },
        )

    score_snapshot(mirrored, config=config(), now=NOW)
    mirrored["portfolio"] = snap.portfolio_counters(mirrored)
    return mirrored


def cleared(base: dict) -> dict:
    """A portfolio where nothing scores: the page has to say so rather than rank noise."""
    clear = deepcopy(base)
    for entry in clear["packages"].values():
        entry["stale"] = False
        entry["never_observed"] = False
        entry["error"] = None
        entry["score"] = {"value": 0, "reasons": [], "stale": False}
        if entry.get("ci"):
            entry["ci"]["consecutive_failures"] = 0
            entry["ci"]["red_since"] = None
        if entry.get("cran"):
            entry["cran"]["deadline"] = None
        if entry.get("tickets"):
            entry["tickets"]["issues_no_maintainer_reply"] = 0
            entry["tickets"]["pull_requests_awaiting_review"] = 0
        if entry.get("release"):
            entry["release"]["commits_by_type"] = {}
    clear["portfolio"] = snap.portfolio_counters(clear)
    return clear


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / "repos.yml").write_text(yaml.dump(INVENTORY, default_flow_style=False, sort_keys=False))

    previous = collect_fixture()
    snap.write(previous, FIXTURES / "snapshot_previous.json")

    # This reading loses one repository entirely, which is what makes one row stale and one -- a
    # package that was never readable -- distinguishable from a row of measured zeros.
    current = collect_fixture(missing=("ghost/missing",), previous=previous)
    snap.write(current, FIXTURES / "snapshot.json")
    snap.write(with_mirror_groups(current), FIXTURES / "snapshot_mirrors.json")
    snap.write(cleared(current), FIXTURES / "snapshot_clear.json")
    print(f"wrote fixtures to {FIXTURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
