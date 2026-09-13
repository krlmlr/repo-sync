"""The snapshot: the one document collection writes and everything else reads.

It is a contract before it is a file. Strangers read it -- a `jq` one-liner, an agent choosing
what to work on, the page itself -- so the schema version travels with the data, field names are
stable, and a field is added or deprecated rather than repurposed.

The group names are data here rather than prose in a script, because publication has to remove a
group by name: a field added to the workspace group later is then excluded by having been added to
a group that is already stripped, with no second change anywhere.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# One name per metric family, in the order the page presents them.
GROUPS = (
    "identity",
    "release",
    "ci",
    "cran",
    "tickets",
    "activity",
    "template",
    "workspace",
    "score",
)

# The groups that describe this machine rather than the package.
# Publication removes these by name; see `strip_local_groups`.
LOCAL_GROUPS = ("workspace",)

# The groups that only a machine holding the mirrors can fill in.
MIRROR_GROUPS = ("template", "workspace")


def iso(moment: datetime) -> str:
    """The one timestamp format in the document: UTC, seconds, `Z`."""
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utcnow() -> str:
    return iso(datetime.now(timezone.utc))


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_days(value: str | None, *, now: datetime | None = None) -> int | None:
    """Whole days between `value` and now, or None when there is no `value` to age."""
    parsed = parse_time(value)
    if parsed is None:
        return None
    reference = now or datetime.now(timezone.utc)
    return max(0, int((reference - parsed).total_seconds() // 86400))


def new_entry(slug: str, org: str, repo: str, *, is_template: bool = False) -> dict[str, Any]:
    """An entry with every group present and empty, so a consumer never has to ask whether a key exists."""
    entry: dict[str, Any] = {
        "slug": slug,
        "org": org,
        "repo": repo,
        "is_template": is_template,
        "observed_at": None,
        "stale": False,
        "never_observed": False,
        "error": None,
    }
    for group in GROUPS:
        entry[group] = None
    return entry


def new_snapshot(
    *, template_slug: str, groups_collected: dict[str, bool], collected_at: str | None = None
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "collected_at": collected_at or utcnow(),
        "template_slug": template_slug,
        "groups": list(GROUPS),
        "groups_collected": dict(groups_collected),
        "requests": {},
        "failures": [],
        "packages": {},
    }


def write(snapshot: dict[str, Any], path: Path) -> None:
    """Write atomically, and with a trailing newline, so a half-written file never reads as a snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dumps(snapshot))
    tmp.replace(path)


def dumps(snapshot: dict[str, Any]) -> str:
    """The canonical serialisation: insertion order preserved, so two runs over one reading are byte-identical."""
    return json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"


def read(path: Path) -> dict[str, Any] | None:
    """The previous snapshot, or None when there is none to carry values forward from.

    A snapshot from a schema we no longer speak is treated as absent rather than as data:
    carrying forward fields that meant something else is worse than a row marked never observed.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        return None
    return data


def carry_forward(previous_entry: dict[str, Any] | None, entry: dict[str, Any], error: str) -> dict[str, Any]:
    """Keep a package's last known values when it cannot be read, stamped with when they were true.

    The alternative -- dropping the row, or writing absent values -- reads as a measured zero on the
    page and in the document, which is the one thing a portfolio reading must never do.
    """
    carried = dict(entry)
    carried["error"] = error
    carried["stale"] = True
    if previous_entry is None:
        carried["never_observed"] = True
        carried["observed_at"] = None
        return carried

    for group in GROUPS:
        carried[group] = previous_entry.get(group)
    carried["observed_at"] = previous_entry.get("observed_at")
    carried["never_observed"] = bool(previous_entry.get("never_observed")) and previous_entry.get("observed_at") is None
    if carried["score"]:
        carried["score"] = dict(carried["score"], stale=True)
    return carried


def strip_local_groups(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The snapshot as published: the local groups removed by name, for every entry.

    By name rather than by field list: whatever the workspace group grows later is dropped with it,
    which is what keeps an added field from being published by having been forgotten here.
    """
    published = dict(snapshot)
    published["groups"] = [g for g in snapshot.get("groups", GROUPS) if g not in LOCAL_GROUPS]
    published["groups_collected"] = {
        name: value for name, value in snapshot.get("groups_collected", {}).items() if name not in LOCAL_GROUPS
    }
    published["packages"] = {
        slug: {key: value for key, value in entry.items() if key not in LOCAL_GROUPS}
        for slug, entry in snapshot.get("packages", {}).items()
    }
    return published


def portfolio_counters(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The reading as a whole, in the few numbers a trend is made of.

    This is the fact no API holds: how many packages were red, how many were due a release, how
    many issues were open on a given day is something only the collection ever computed.
    """
    packages = snapshot.get("packages", {})
    counters = {
        "collected_at": snapshot.get("collected_at"),
        "packages": len(packages),
        "stale": 0,
        "ci_failing": 0,
        "cran_not_ok": 0,
        "unreleased_commits": 0,
        "open_issues": 0,
        "open_pull_requests": 0,
        "issues_no_maintainer_reply": 0,
        "dormant": 0,
        "attention_total": 0.0,
    }
    for entry in packages.values():
        if entry.get("stale"):
            counters["stale"] += 1
        ci = entry.get("ci") or {}
        if ci.get("consecutive_failures"):
            counters["ci_failing"] += 1
        cran = entry.get("cran") or {}
        if cran.get("worst_status") not in (None, "OK"):
            counters["cran_not_ok"] += 1
        release = entry.get("release") or {}
        counters["unreleased_commits"] += release.get("commits_since") or 0
        tickets = entry.get("tickets") or {}
        counters["open_issues"] += tickets.get("open_issues") or 0
        counters["open_pull_requests"] += tickets.get("open_pull_requests") or 0
        counters["issues_no_maintainer_reply"] += tickets.get("issues_no_maintainer_reply") or 0
        activity = entry.get("activity") or {}
        if activity.get("dormant"):
            counters["dormant"] += 1
        score = entry.get("score") or {}
        counters["attention_total"] += score.get("value") or 0
    counters["attention_total"] = round(counters["attention_total"], 2)
    return counters
