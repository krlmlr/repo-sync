"""How much a package is asking for attention, and why.

A composite nobody can interrogate is believed once and ignored thereafter, so the score is never
the only thing recorded: every reason that contributed carries its own number, the contributions
sum to the total, and the weights that produced them are configuration rather than code.

The score ranks and nothing else. Nothing here files an issue, cuts a release or opens a pull
request on the strength of a number.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import Config
from .snapshot import age_days, parse_time


def _capped(value: float, cap: float) -> float:
    return min(value, cap) if cap else value


def score_entry(entry: dict[str, Any], *, config: Config, now: datetime) -> dict[str, Any]:
    """The score for one entry, with one reason per thing that is actually true about it."""
    reasons: list[dict[str, Any]] = []

    ci = entry.get("ci") or {}
    red_days = age_days(ci.get("red_since"), now=now)
    if ci.get("consecutive_failures") and red_days is not None:
        contribution = _capped(red_days * config.weight("ci_red_per_day"), config.weight("ci_red_max"))
        reasons.append(
            {
                "code": "ci_red",
                "label": f"CI red for {red_days} day{'s' if red_days != 1 else ''}",
                "detail": {"days": red_days, "consecutive_failures": ci.get("consecutive_failures")},
                "contribution": round(contribution, 2),
            }
        )

    cran = entry.get("cran") or {}
    deadline_days = _days_until(cran.get("deadline"), now)
    if deadline_days is not None:
        # Closer is worse, and past is worst: the base is what having a deadline at all costs.
        counted = config.weight("cran_deadline_days_counted")
        urgency = max(0.0, counted - deadline_days) * config.weight("cran_deadline_per_day_remaining")
        contribution = config.weight("cran_deadline_base") + urgency
        reasons.append(
            {
                "code": "cran_deadline",
                "label": f"CRAN deadline {cran.get('deadline')}",
                "detail": {"deadline": cran.get("deadline"), "days_remaining": deadline_days},
                "contribution": round(contribution, 2),
            }
        )

    release = entry.get("release") or {}
    by_type = release.get("commits_by_type") or {}
    user_facing = (by_type.get("feat") or 0) + (by_type.get("fix") or 0)
    if user_facing:
        # Scaled by age: three fixes from this morning are not the same debt as three from March.
        age = age_days(release.get("oldest_unreleased_at"), now=now) or 0
        factor = min(
            1.0 + age / config.weight("unreleased_age_scale_days"),
            config.weight("unreleased_age_factor_max"),
        )
        contribution = _capped(
            user_facing * config.weight("unreleased_user_facing_per_commit") * factor,
            config.weight("unreleased_max"),
        )
        reasons.append(
            {
                "code": "unreleased",
                "label": f"{user_facing} user-facing commit{'s' if user_facing != 1 else ''} unreleased",
                "detail": {
                    "feat": by_type.get("feat") or 0,
                    "fix": by_type.get("fix") or 0,
                    "oldest_age_days": age,
                },
                "contribution": round(contribution, 2),
            }
        )

    tickets = entry.get("tickets") or {}
    unanswered = tickets.get("issues_no_maintainer_reply") or 0
    if unanswered:
        contribution = _capped(
            unanswered * config.weight("issue_no_reply_per_issue"), config.weight("issue_no_reply_max")
        )
        reasons.append(
            {
                "code": "issues_no_reply",
                "label": f"{unanswered} issue{'s' if unanswered != 1 else ''} with no maintainer reply",
                "detail": {"issues": unanswered},
                "contribution": round(contribution, 2),
            }
        )

    awaiting = tickets.get("pull_requests_awaiting_review") or 0
    if awaiting:
        contribution = _capped(
            awaiting * config.weight("pr_awaiting_review_per_pr"), config.weight("pr_awaiting_review_max")
        )
        reasons.append(
            {
                "code": "prs_awaiting_review",
                "label": f"{awaiting} pull request{'s' if awaiting != 1 else ''} awaiting review",
                "detail": {"pull_requests": awaiting},
                "contribution": round(contribution, 2),
            }
        )

    template = entry.get("template") or {}
    outstanding = template.get("outstanding") or 0 if template.get("collected") else 0
    if outstanding:
        contribution = _capped(
            outstanding * config.weight("template_commit_per_commit"), config.weight("template_commit_max")
        )
        reasons.append(
            {
                "code": "template_outstanding",
                "label": f"{outstanding} template commit{'s' if outstanding != 1 else ''} outstanding",
                "detail": {"commits": outstanding, "oldest": template.get("oldest_outstanding_at")},
                "contribution": round(contribution, 2),
            }
        )

    return {
        # The rounded contributions are what is shown, so the total is their sum and not a
        # separately rounded number that fails to add up in front of the reader.
        "value": round(sum(reason["contribution"] for reason in reasons), 2),
        "reasons": reasons,
        "stale": bool(entry.get("stale")),
    }


def _days_until(date: str | None, now: datetime) -> int | None:
    """Days from now to a date, negative once it is in the past -- which is when it matters most."""
    if not date:
        return None
    parsed = parse_time(f"{date}T00:00:00Z")
    if parsed is None:
        return None
    return int((parsed - now).total_seconds() // 86400)


def score_snapshot(snapshot: dict[str, Any], *, config: Config, now: datetime) -> dict[str, Any]:
    for entry in snapshot.get("packages", {}).values():
        entry["score"] = score_entry(entry, config=config, now=now)
    return snapshot
