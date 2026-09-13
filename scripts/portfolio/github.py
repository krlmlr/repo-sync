"""What GitHub knows about a repository, in as few requests as it can be asked for.

Two shapes of question, two APIs. The repository facts -- identity, releases, commits, issues,
pull requests -- are one aliased GraphQL query per ten repositories, because GraphQL is the only
way to ask forty-six repositories anything without paying forty-six round trips for it. Workflow
runs stay on REST: they are paginated by run rather than by repository, filtered by branch, and
are the one thing here that genuinely costs a request per package.

Everything below the client is a pure function over a parsed response, so the derivations are
tested against recorded payloads and need no network to exercise.
"""

from __future__ import annotations

import json
import re
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .config import Config
from .dcf import parse_dcf
from .snapshot import age_days, parse_time
from .transport import Client, Response, Unreadable

GRAPHQL_URL = "https://api.github.com/graphql"
REST_ROOT = "https://api.github.com"

# The prefixes Conventional Commits defines, plus the two the repositories here actually use.
# A subject outside this set is unclassified rather than forced into `chore`:
# a bucket that absorbs everything unrecognised stops being a reading of anything.
CONVENTIONAL_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
CONVENTIONAL_SUBJECT = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]*\))?(?P<breaking>!)?:\s")

# The associations GitHub reports for someone who can act on the repository.
# Public on every comment, which is what makes this readable without push access of our own.
MAINTAINER_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
PUSH_PERMISSIONS = frozenset({"ADMIN", "MAINTAIN", "WRITE"})

# A conclusion that says something about the code, as against one that says the run was stopped.
CI_PASS = frozenset({"success"})
CI_FAIL = frozenset({"failure", "timed_out", "startup_failure"})

_REPO_FIELDS = """
fragment facts on Repository {
  nameWithOwner
  description
  url
  isArchived
  isPrivate
  viewerPermission
  descriptionFile: object(expression: "HEAD:DESCRIPTION") { ... on Blob { text } }
  defaultBranchRef {
    name
    target {
      ... on Commit {
        committedDate
        recent: history(first: $commitLimit) {
          totalCount
          nodes { oid committedDate messageHeadline }
        }
        window: history(since: $activitySince) { totalCount }
        authors: history(since: $authorsSince, first: 100) {
          totalCount
          nodes { author { user { login } name email } }
        }
      }
    }
  }
  releases(first: 5, orderBy: { field: CREATED_AT, direction: DESC }) {
    nodes { tagName name url publishedAt createdAt isDraft isPrerelease }
  }
  issues(states: OPEN, first: $issueLimit, orderBy: { field: CREATED_AT, direction: ASC }) {
    totalCount
    nodes {
      number url createdAt updatedAt authorAssociation
      comments(last: $commentLimit) { totalCount nodes { authorAssociation } }
    }
  }
  pullRequests(states: OPEN, first: $pullRequestLimit, orderBy: { field: CREATED_AT, direction: ASC }) {
    totalCount
    nodes {
      number url createdAt updatedAt isDraft authorAssociation reviewDecision
      author { __typename login }
      reviews(first: 1) { totalCount }
    }
  }
}
"""


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_query(slugs: Iterable[str]) -> tuple[str, dict[str, str]]:
    """One query over many repositories, and the alias each answer comes back under."""
    aliases: dict[str, str] = {}
    lines = []
    for index, slug in enumerate(slugs):
        org, _, repo = slug.partition("/")
        alias = f"r{index}"
        aliases[alias] = slug
        lines.append(f'  {alias}: repository(owner: "{_escape(org)}", name: "{_escape(repo)}") {{ ...facts }}')
    header = (
        "query($commitLimit: Int!, $issueLimit: Int!, $pullRequestLimit: Int!, $commentLimit: Int!, "
        "$activitySince: GitTimestamp!, $authorsSince: GitTimestamp!) {"
    )
    body = "\n".join([header, *lines, "}"])
    return body + _REPO_FIELDS, aliases


class GitHubSource:
    """The repository facts and the workflow runs, counted and retried by the shared client."""

    def __init__(self, client: Client, token: str, config: Config, *, now: datetime | None = None):
        self.client = client
        self.token = token
        self.config = config
        self.now = now or datetime.now(timezone.utc)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "repo-sync-dashboard",
        }

    def repository_facts(self, slugs: list[str]) -> dict[str, Any]:
        """The facts for one batch, keyed by slug.

        A repository that comes back null -- renamed, gone, or invisible to this credential -- is
        absent from the result rather than present and empty, so the caller marks that one package
        unreadable and keeps the other nine.
        """
        query, aliases = build_query(slugs)
        variables = {
            "commitLimit": self.config.limit("commits_per_repo"),
            "issueLimit": self.config.limit("issues_per_repo"),
            "pullRequestLimit": self.config.limit("pull_requests_per_repo"),
            "commentLimit": self.config.limit("comments_per_issue"),
            "activitySince": _iso(self.now - timedelta(days=self.config.window("activity_days"))),
            "authorsSince": _iso(self.now - timedelta(days=self.config.window("authors_days"))),
        }
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        response = self.client.request("POST", GRAPHQL_URL, kind="graphql", headers=self._headers(), body=body)
        if response.status != 200:
            raise Unreadable(f"GraphQL returned {response.status}: {_short(response)}")
        payload = response.json()
        data = payload.get("data") or {}
        if not data:
            raise Unreadable(f"GraphQL returned no data: {_errors(payload)}")
        facts: dict[str, Any] = {}
        for alias, slug in aliases.items():
            node = data.get(alias)
            if node:
                facts[slug] = node
        return facts

    def workflow_runs(self, slug: str, branch: str) -> list[dict[str, Any]]:
        """The runs on the default branch inside the retention window, oldest first.

        Bounded by pages rather than by patience: a repository that runs a hundred workflows a week
        is not worth ten requests, and the window actually covered is recorded beside the series.
        """
        since = (self.now - timedelta(days=self.config.window("ci_days"))).date().isoformat()
        runs: list[dict[str, Any]] = []
        per_page = self.config.limit("workflow_runs_per_page")
        for page in range(1, self.config.limit("workflow_run_pages") + 1):
            url = (
                f"{REST_ROOT}/repos/{slug}/actions/runs"
                f"?branch={branch}&per_page={per_page}&page={page}&created=%3E%3D{since}"
            )
            response = self.client.request("GET", url, kind="rest", headers=self._headers())
            if response.status == 404:
                # No Actions on this repository at all, which is a fact and not a failure.
                return []
            if response.status != 200:
                raise Unreadable(f"workflow runs for {slug} returned {response.status}: {_short(response)}")
            payload = response.json()
            page_runs = payload.get("workflow_runs") or []
            runs.extend(page_runs)
            if len(page_runs) < per_page:
                break
        return [run_entry(run) for run in sorted(runs, key=lambda run: run.get("created_at") or "")]


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _short(response: Response) -> str:
    return response.text()[:200].replace("\n", " ")


def _errors(payload: dict[str, Any]) -> str:
    return "; ".join(error.get("message", "") for error in payload.get("errors", []))[:200]


def run_entry(run: dict[str, Any]) -> dict[str, Any]:
    started = parse_time(run.get("run_started_at") or run.get("created_at"))
    finished = parse_time(run.get("updated_at"))
    duration = int((finished - started).total_seconds()) if started and finished else None
    return {
        "workflow": run.get("name"),
        "conclusion": run.get("conclusion"),
        "status": run.get("status"),
        "created_at": run.get("created_at"),
        "duration_seconds": duration,
        "url": run.get("html_url"),
    }


def classify_subjects(subjects: Iterable[str]) -> dict[str, int]:
    """Conventional Commits types to counts, with everything else under `unclassified`.

    The buckets sum to the total by construction, which is what makes the breakdown readable as a
    description of the same commits the count above it came from.
    """
    counts: dict[str, int] = {}
    for subject in subjects:
        match = CONVENTIONAL_SUBJECT.match(subject or "")
        kind = match.group("type").lower() if match else None
        bucket = kind if kind in CONVENTIONAL_TYPES else "unclassified"
        counts[bucket] = counts.get(bucket, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def identity_group(raw: dict[str, Any]) -> dict[str, Any]:
    """Who the repository is, and whether it is an R package at all.

    From a root `DESCRIPTION` rather than from a hand-kept map, because `duckdb-r` ships `duckdb`
    and `rigraph` ships `igraph`, and a map of those is a file that goes stale in silence.
    """
    blob = raw.get("descriptionFile") or {}
    fields = parse_dcf(blob.get("text") or "") if blob.get("text") else {}
    package = fields.get("Package")
    branch_ref = raw.get("defaultBranchRef") or {}
    slug = raw.get("nameWithOwner") or ""
    branch = branch_ref.get("name")
    return {
        "default_branch": branch,
        # Links are fields rather than something the page builds, so a consumer that is not the
        # page reaches the same places, and the page computes nothing it would have to reimplement.
        "links": {
            "repository": raw.get("url") or f"https://github.com/{slug}",
            "actions": f"https://github.com/{slug}/actions"
            + (f"?query=branch%3A{branch}" if branch else ""),
            # `actions-sync` owns the per-workflow view and publishes it as one page.
            "actions_sync": "https://krlmlr.github.io/actions-sync/",
        },
        "description": raw.get("description"),
        "url": raw.get("url"),
        "visibility": "private" if raw.get("isPrivate") else "public",
        "archived": bool(raw.get("isArchived")),
        "is_r_package": package is not None,
        "package": package,
        "version": fields.get("Version") if package else None,
        "viewer_can_push": raw.get("viewerPermission") in PUSH_PERMISSIONS,
    }


def release_group(raw: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """Where the package stands against its own last release.

    Commits since are the ones on the default branch newer than the release, taken from the recent
    history the batch already carries: one more query per package to count them exactly would cost
    more than the answer is worth, so a history that does not reach back far enough says so.
    """
    nodes = (raw.get("releases") or {}).get("nodes") or []
    published = [node for node in nodes if not node.get("isDraft")]
    latest = published[0] if published else None
    can_push = raw.get("viewerPermission") in PUSH_PERMISSIONS
    has_draft = any(node.get("isDraft") for node in nodes)

    history = ((raw.get("defaultBranchRef") or {}).get("target") or {}).get("recent") or {}
    commits = history.get("nodes") or []
    released_at = parse_time(latest.get("publishedAt") or latest.get("createdAt")) if latest else None

    since_commits = []
    if released_at is not None:
        for commit in commits:
            committed = parse_time(commit.get("committedDate"))
            if committed is not None and committed > released_at:
                since_commits.append(commit)

    group: dict[str, Any] = {
        "latest_tag": latest.get("tagName") if latest else None,
        "latest_url": latest.get("url") if latest else None,
        "latest_published_at": latest.get("publishedAt") or latest.get("createdAt") if latest else None,
        "latest_age_days": None,
        "commits_since": None,
        "commits_since_truncated": False,
        "commits_by_type": None,
        "oldest_unreleased_at": None,
        # Three states, not two: a draft we cannot see is not a draft that is not there.
        "draft_release": "present" if (can_push and has_draft) else ("none" if can_push else "unavailable"),
        "cran_version": None,
        "cran_published_at": None,
        "cran_age_days": None,
        "ahead_of_cran": None,
    }
    if latest is None:
        return group

    group["latest_age_days"] = age_days(group["latest_published_at"], now=now)
    group["commits_since"] = len(since_commits)
    group["commits_by_type"] = classify_subjects(commit.get("messageHeadline") or "" for commit in since_commits)
    # Every commit fetched is newer than the release, so the true count may be higher than this one.
    group["commits_since_truncated"] = bool(since_commits) and len(since_commits) == len(commits)
    if since_commits:
        group["oldest_unreleased_at"] = min(commit.get("committedDate") for commit in since_commits)
    return group


def ci_group(series: list[dict[str, Any]], *, window_days: int, now: datetime) -> dict[str, Any]:
    """The default branch's run history, and the four things worth deriving from it.

    Consecutive failures are counted from the newest run backwards and stop at the first pass, so a
    repository that alternates is flaky rather than broken -- a distinction the page has to keep,
    because the two want different work.
    """
    if not series:
        return {
            "latest_conclusion": None,
            "latest_run_at": None,
            "latest_run_url": None,
            "runs": [],
            "window_days": window_days,
            "window_from": None,
            "window_to": None,
            "success_rate": None,
            "median_duration_seconds": None,
            "consecutive_failures": 0,
            "red_since": None,
        }

    decisive = [run for run in series if run.get("conclusion") in CI_PASS | CI_FAIL]
    passes = sum(1 for run in decisive if run.get("conclusion") in CI_PASS)
    durations = [run["duration_seconds"] for run in series if run.get("duration_seconds") is not None]

    consecutive = 0
    red_since = None
    for run in reversed(decisive):
        if run.get("conclusion") in CI_FAIL:
            consecutive += 1
            red_since = run.get("created_at")
            continue
        break

    return {
        "latest_conclusion": series[-1].get("conclusion"),
        "latest_run_at": series[-1].get("created_at"),
        "latest_run_url": series[-1].get("url"),
        "runs": series,
        "window_days": window_days,
        # What the source actually retained, which is shorter than the window for a quiet package.
        "window_from": series[0].get("created_at"),
        "window_to": series[-1].get("created_at"),
        "success_rate": round(passes / len(decisive), 4) if decisive else None,
        "median_duration_seconds": int(statistics.median(durations)) if durations else None,
        "consecutive_failures": consecutive,
        "red_since": red_since,
    }


def tickets_group(raw: dict[str, Any], *, config: Config, now: datetime) -> dict[str, Any]:
    """Open issues and pull requests, and the cuts of them that carry an action.

    A maintainer reply is identified by the comment's public `author_association`, which is
    readable without push access -- the permission lookup that would be exact is not available for
    repositories that are not ours, so the public signal is the one that works everywhere.
    """
    issues = raw.get("issues") or {}
    pulls = raw.get("pullRequests") or {}
    issue_nodes = issues.get("nodes") or []
    pull_nodes = pulls.get("nodes") or []
    stale_after = config.window("stale_issue_days")
    review_after = config.window("review_wait_days")
    comment_limit = config.limit("comments_per_issue")

    no_reply = 0
    stale_issues = 0
    for issue in issue_nodes:
        comments = issue.get("comments") or {}
        associations = [node.get("authorAssociation") for node in comments.get("nodes") or []]
        answered = any(association in MAINTAINER_ASSOCIATIONS for association in associations)
        # A thread longer than we fetched, with no maintainer among the comments we did fetch, is
        # unknown rather than unanswered: guessing in the direction of more work is still guessing.
        truncated = (comments.get("totalCount") or 0) > comment_limit
        if not answered and not truncated:
            no_reply += 1
        if (age_days(issue.get("updatedAt"), now=now) or 0) >= stale_after:
            stale_issues += 1

    outside = 0
    bots = 0
    drafts = 0
    awaiting = 0
    for pull in pull_nodes:
        author = pull.get("author") or {}
        if author.get("__typename") == "Bot" or (author.get("login") or "").endswith("[bot]"):
            bots += 1
        elif pull.get("authorAssociation") not in MAINTAINER_ASSOCIATIONS:
            outside += 1
        if pull.get("isDraft"):
            drafts += 1
            continue
        reviewed = (pull.get("reviews") or {}).get("totalCount") or 0
        waited = age_days(pull.get("createdAt"), now=now) or 0
        if not reviewed and pull.get("reviewDecision") in (None, "REVIEW_REQUIRED") and waited >= review_after:
            awaiting += 1

    return {
        "open_issues": issues.get("totalCount") or 0,
        "open_pull_requests": pulls.get("totalCount") or 0,
        "issues_sampled": len(issue_nodes),
        "pull_requests_sampled": len(pull_nodes),
        "issues_no_maintainer_reply": no_reply,
        "issues_stale": stale_issues,
        "issues_stale_after_days": stale_after,
        "pull_requests_outside": outside,
        "pull_requests_bot": bots,
        "pull_requests_draft": drafts,
        "pull_requests_awaiting_review": awaiting,
        "pull_requests_review_after_days": review_after,
        "oldest_issue_age_days": age_days(issue_nodes[0].get("createdAt"), now=now) if issue_nodes else None,
        "oldest_pull_request_age_days": age_days(pull_nodes[0].get("createdAt"), now=now) if pull_nodes else None,
    }


def activity_group(raw: dict[str, Any], *, config: Config, now: datetime) -> dict[str, Any]:
    """How alive the package is: last commit, recent commits, distinct authors, dormancy."""
    target = ((raw.get("defaultBranchRef") or {}).get("target")) or {}
    window = target.get("window") or {}
    authors = target.get("authors") or {}
    identities = set()
    for commit in authors.get("nodes") or []:
        author = commit.get("author") or {}
        user = author.get("user") or {}
        identities.add(user.get("login") or author.get("email") or author.get("name"))
    identities.discard(None)

    last_commit_at = target.get("committedDate")
    since_last = age_days(last_commit_at, now=now)
    dormancy = config.window("dormancy_days")
    return {
        "last_commit_at": last_commit_at,
        "last_commit_age_days": since_last,
        "commits_recent": window.get("totalCount"),
        "commits_recent_window_days": config.window("activity_days"),
        "authors_recent": len(identities) if authors else None,
        "authors_window_days": config.window("authors_days"),
        "authors_truncated": (authors.get("totalCount") or 0) > len(authors.get("nodes") or []),
        "dormant": since_last is not None and since_last >= dormancy,
        "dormancy_days": dormancy,
    }
