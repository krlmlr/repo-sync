"""One run: the inventory in, one snapshot out, whatever happened in between.

The discipline is the one `fail` and `report_failures` set for the shell tools, in the shape an
API-bound tool needs it: a package that cannot be read keeps its last known values marked with when
they were true, the run carries on to the next package, the failures are named at the end, and the
exit status is non-zero for the scheduler while the snapshot is written for the human.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import snapshot as snap
from .config import Config
from .cran import CranSource
from .dcf import compare_versions
from .github import GitHubSource, activity_group, ci_group, identity_group, release_group, tickets_group
from .inventory import Inventory
from .mirrors import GitRunner, mirrors_present, template_group, workspace_group
from .score import score_snapshot
from .snapshot import age_days
from .transport import Unreadable


def collect(
    *,
    inventory: Inventory,
    config: Config,
    github: GitHubSource,
    cran: CranSource | None,
    mirrors_dir: Path,
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    have_mirrors = mirrors_present(mirrors_dir)
    result = snap.new_snapshot(
        template_slug=inventory.template_slug,
        groups_collected={name: have_mirrors for name in snap.MIRROR_GROUPS},
        # The collection's own clock, so a run against recorded responses is reproducible.
        collected_at=snap.iso(now),
    )
    previous_packages = (previous or {}).get("packages", {})
    runner = GitRunner()
    failures: list[str] = []

    batch_size = config.limit("graphql_batch")
    entries = list(inventory)
    for start in range(0, len(entries), batch_size):
        batch = entries[start : start + batch_size]
        slugs = [entry.slug for entry in batch]
        try:
            facts = github.repository_facts(slugs)
            batch_error = None
        except Unreadable as exc:
            facts, batch_error = {}, str(exc)
            log(f"FAIL: repository facts for {len(slugs)} repositories: {exc}")

        for entry in batch:
            record = snap.new_entry(entry.slug, entry.org, entry.repo, is_template=entry.is_template)
            raw = facts.get(entry.slug)
            try:
                if raw is None:
                    raise Unreadable(batch_error or "repository not readable with this credential")
                _fill_remote_groups(record, raw, github=github, cran=cran, config=config, now=now)
                record["observed_at"] = snap.iso(now)
            except Unreadable as exc:
                log(f"FAIL: {entry.slug}: {exc}")
                failures.append(entry.slug)
                record = snap.carry_forward(previous_packages.get(entry.slug), record, str(exc))

            if have_mirrors:
                _fill_mirror_groups(
                    record,
                    runner=runner,
                    mirrors_dir=mirrors_dir,
                    template_slug=inventory.template_slug,
                )
            result["packages"][entry.slug] = record

    score_snapshot(result, config=config, now=now)
    result["requests"] = dict(sorted(github.client.counts.items())) | {"total": github.client.total}
    result["failures"] = sorted(failures)
    # The reading as a whole, as fields: the page shows these and the history is made of them,
    # and neither has to re-derive a portfolio-level number from forty-six entries.
    result["portfolio"] = snap.portfolio_counters(result)
    return result


def _fill_remote_groups(
    record: dict[str, Any],
    raw: dict[str, Any],
    *,
    github: GitHubSource,
    cran: CranSource | None,
    config: Config,
    now: datetime,
) -> None:
    record["identity"] = identity_group(raw)
    record["release"] = release_group(raw, now=now)
    record["tickets"] = tickets_group(raw, config=config, now=now)
    record["activity"] = activity_group(raw, config=config, now=now)

    branch = record["identity"].get("default_branch")
    runs = github.workflow_runs(record["slug"], branch) if branch else []
    record["ci"] = ci_group(runs, window_days=config.window("ci_days"), now=now)

    package = record["identity"].get("package")
    if package and cran is not None:
        group = cran.package(package)
        record["cran"] = group
        release = record["release"]
        release["cran_version"] = group.get("version")
        release["cran_published_at"] = group.get("published_at")
        release["cran_age_days"] = age_days(_as_timestamp(group.get("published_at")), now=now)
        comparison = compare_versions(record["identity"].get("version"), group.get("version"))
        release["ahead_of_cran"] = comparison > 0 if comparison is not None else None


def _fill_mirror_groups(
    record: dict[str, Any],
    *,
    runner: GitRunner,
    mirrors_dir: Path,
    template_slug: str,
) -> None:
    """The two groups that come from disk, recorded as uncollected when this mirror is not there.

    Uncollected rather than empty: a mirror nobody has cloned yet is not a mirror that is in step.
    """
    mirror = mirrors_dir / record["slug"]
    if record["slug"] == template_slug:
        record["template"] = {"collected": False, "reason": "the template is not measured against itself"}
    elif not (mirror / ".git").is_dir():
        record["template"] = {"collected": False, "reason": f"no mirror at mirrors/{record['slug']}"}
    else:
        record["template"] = template_group(runner, mirror, mirrors_dir / f"{template_slug}.git")

    if (mirror / ".git").is_dir():
        record["workspace"] = workspace_group(runner, mirror)
    else:
        record["workspace"] = {"collected": False, "reason": f"no mirror at mirrors/{record['slug']}"}


def _as_timestamp(date: str | None) -> str | None:
    return f"{date}T00:00:00Z" if date and len(date) == 10 else date


def report(result: dict[str, Any], *, log: Callable[[str], None] = print) -> int:
    """The end of a run, in the shape `report_failures` already uses.

    The request count is reported beside the failures for the same reason: a budget that is only
    noticed once it is spent is a budget nobody is managing.
    """
    requests = result.get("requests") or {}
    counted = ", ".join(f"{kind}={count}" for kind, count in requests.items() if kind != "total")
    log(f"\nREQUESTS ({requests.get('total', 0)}): {counted}")
    failures = result.get("failures") or []
    if failures:
        log(f"FAILED ({len(failures)}): {' '.join(failures)}")
        return 1
    return 0
