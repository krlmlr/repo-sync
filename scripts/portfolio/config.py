"""The numbers the reading depends on, kept out of the code.

Windows, thresholds and score weights are the part of this tool that is opinion rather than fact,
and an opinion nobody can change without editing Python is one that gets argued with instead of
tuned. `dashboard.yml` holds them; this module is the defaults and the merge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_WINDOWS: dict[str, int] = {
    # Ninety days is not a choice: it is what GitHub retains of a workflow run.
    "ci_days": 90,
    "activity_days": 90,
    "authors_days": 365,
    "dormancy_days": 365,
    "stale_issue_days": 90,
    "review_wait_days": 14,
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "ci_red_per_day": 0.5,
    "ci_red_max": 30.0,
    "cran_deadline_base": 25.0,
    "cran_deadline_per_day_remaining": 1.0,
    "cran_deadline_days_counted": 30.0,
    "unreleased_user_facing_per_commit": 1.0,
    "unreleased_age_scale_days": 30.0,
    "unreleased_age_factor_max": 3.0,
    "unreleased_max": 30.0,
    "issue_no_reply_per_issue": 0.5,
    "issue_no_reply_max": 10.0,
    "pr_awaiting_review_per_pr": 1.0,
    "pr_awaiting_review_max": 10.0,
    "template_commit_per_commit": 0.5,
    "template_commit_max": 10.0,
}

DEFAULT_COLLECTION: dict[str, int] = {
    # Ten repositories per query: enough to make the whole inventory five queries,
    # few enough that one response stays readable and the node budget stays low.
    "graphql_batch": 10,
    "issues_per_repo": 50,
    "pull_requests_per_repo": 50,
    "comments_per_issue": 10,
    "commits_per_repo": 100,
    "workflow_run_pages": 2,
    "workflow_runs_per_page": 100,
}


@dataclass
class Config:
    windows: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WINDOWS))
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    collection: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_COLLECTION))

    def window(self, name: str) -> int:
        return int(self.windows.get(name, DEFAULT_WINDOWS[name]))

    def weight(self, name: str) -> float:
        return float(self.weights.get(name, DEFAULT_WEIGHTS[name]))

    def limit(self, name: str) -> int:
        return int(self.collection.get(name, DEFAULT_COLLECTION[name]))


def load_config(path: Path | None) -> Config:
    """Defaults, overlaid with whatever the file sets.

    Section by section rather than wholesale, so a file that names one weight keeps every other
    default instead of silently emptying the rest of the section.
    """
    config = Config()
    if path is None or not path.exists():
        return config
    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    for section, target in (
        ("windows", config.windows),
        ("weights", config.weights),
        ("collection", config.collection),
    ):
        values = data.get(section) or {}
        if not isinstance(values, dict):
            raise ValueError(f"{path}: section {section} must be a mapping")
        target.update(values)
    return config
