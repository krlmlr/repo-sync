"""Recorded answers instead of a network.

The collector talks to two services and nothing else, both through one `Transport`. Replacing that
one object with the fake below is what makes every derivation in the collector testable offline --
against payloads whose shape is the shape the live services return, checked in and diffable.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from portfolio.transport import Response, Transport

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

ALIAS = re.compile(r'(r\d+): repository\(owner: "([^"]+)", name: "([^"]+)"\)')


def ago(days: float) -> str:
    return (NOW - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class FakeTransport(Transport):
    """GitHub and CRAN, as far as this collector can tell.

    `repos` is keyed by slug: a slug that is absent from it comes back as a null alias, which is
    what GitHub returns for a repository the credential cannot see, and is the failure path the
    per-package isolation is built around.
    """

    def __init__(
        self,
        *,
        repos: dict[str, dict[str, Any]] | None = None,
        runs: dict[str, list[dict[str, Any]]] | None = None,
        cran: dict[str, tuple[int, str]] | None = None,
        graphql_error: str | None = None,
        cran_down: bool = False,
    ):
        self.repos = repos or {}
        self.runs = runs or {}
        self.cran = cran or {}
        self.graphql_error = graphql_error
        self.cran_down = cran_down
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, *, headers=None, body=None) -> Response:
        self.calls.append((method, url))
        if "graphql" in url:
            return self._graphql(body)
        if "api.github.com" in url:
            return self._runs(url)
        return self._cran(url)

    def _graphql(self, body: bytes | None) -> Response:
        if self.graphql_error:
            return Response(502, {}, self.graphql_error.encode())
        query = json.loads(body or b"{}").get("query", "")
        data = {alias: self.repos.get(f"{org}/{repo}") for alias, org, repo in ALIAS.findall(query)}
        return Response(200, {}, json.dumps({"data": data}).encode())

    def _runs(self, url: str) -> Response:
        slug = url.split("/repos/", 1)[1].split("/actions")[0]
        page = int(re.search(r"[?&]page=(\d+)", url).group(1)) if "page=" in url else 1
        runs = self.runs.get(slug, []) if page == 1 else []
        return Response(200, {}, json.dumps({"workflow_runs": runs}).encode())

    def _cran(self, url: str) -> Response:
        if self.cran_down:
            return Response(503, {}, b"service unavailable")
        name = url.rstrip("/").split("/")[-1]
        if url.endswith("DESCRIPTION"):
            name = url.split("/web/packages/")[1].split("/")[0]
            entry = self.cran.get(name)
            if entry is None:
                return Response(404, {}, b"not found")
            return Response(200, {}, entry[1].encode())
        package = name.replace("check_results_", "").replace(".html", "")
        entry = self.cran.get(package)
        if entry is None or entry[0] is None:
            return Response(404, {}, b"not found")
        return Response(200, {}, str(entry[0]).encode())


def cran_pages(package: str, *, version: str, published: str, checks: str | None) -> tuple[str, str]:
    """A CRAN answer: the `DESCRIPTION` CRAN serves, and the check page for it."""
    description = f"Package: {package}\nVersion: {version}\nDate/Publication: {published} 09:20:02 UTC\n"
    return (checks or "", description)


def check_page(name: str) -> str:
    """One of the check pages recorded from the live service during implementation."""
    return (FIXTURES / "cran" / f"check_results_{name}.html").read_text()


def repository(
    slug: str,
    *,
    description_file: str | None = None,
    default_branch: str | None = "main",
    archived: bool = False,
    private: bool = False,
    permission: str = "READ",
    releases: list[dict[str, Any]] | None = None,
    commits: list[tuple[str, str]] | None = None,
    commits_recent: int = 0,
    authors: list[str] | None = None,
    last_commit: str | None = None,
    issues: list[dict[str, Any]] | None = None,
    issue_total: int | None = None,
    pulls: list[dict[str, Any]] | None = None,
    pull_total: int | None = None,
) -> dict[str, Any]:
    """One repository as the GraphQL batch returns it."""
    node: dict[str, Any] = {
        "nameWithOwner": slug,
        "description": f"{slug} description",
        "url": f"https://github.com/{slug}",
        "isArchived": archived,
        "isPrivate": private,
        "viewerPermission": permission,
        "descriptionFile": {"text": description_file} if description_file else None,
        "defaultBranchRef": None,
        "releases": {"nodes": releases or []},
        "issues": {
            "totalCount": issue_total if issue_total is not None else len(issues or []),
            "nodes": issues or [],
        },
        "pullRequests": {
            "totalCount": pull_total if pull_total is not None else len(pulls or []),
            "nodes": pulls or [],
        },
    }
    if default_branch:
        node["defaultBranchRef"] = {
            "name": default_branch,
            "target": {
                "committedDate": last_commit or ago(1),
                "recent": {
                    "totalCount": len(commits or []),
                    "nodes": [
                        {"oid": f"{index:040x}", "committedDate": when, "messageHeadline": subject}
                        for index, (when, subject) in enumerate(commits or [])
                    ],
                },
                "window": {"totalCount": commits_recent},
                "authors": {
                    "totalCount": len(authors or []),
                    "nodes": [{"author": {"user": {"login": login}, "name": login, "email": None}} for login in authors or []],
                },
            },
        }
    return node


def issue(*, created: str, updated: str | None = None, comments: list[str] | None = None, total: int | None = None) -> dict[str, Any]:
    return {
        "number": 1,
        "url": "https://github.com/example/example/issues/1",
        "createdAt": created,
        "updatedAt": updated or created,
        "authorAssociation": "NONE",
        "comments": {
            "totalCount": total if total is not None else len(comments or []),
            "nodes": [{"authorAssociation": association} for association in comments or []],
        },
    }


def pull_request(
    *,
    created: str,
    association: str = "NONE",
    bot: bool = False,
    draft: bool = False,
    reviews: int = 0,
    decision: str | None = None,
) -> dict[str, Any]:
    return {
        "number": 2,
        "url": "https://github.com/example/example/pull/2",
        "createdAt": created,
        "updatedAt": created,
        "isDraft": draft,
        "authorAssociation": association,
        "reviewDecision": decision,
        "author": {"__typename": "Bot" if bot else "User", "login": "dependabot[bot]" if bot else "someone"},
        "reviews": {"totalCount": reviews},
    }


def run(*, conclusion: str, created: str, duration: int = 600, workflow: str = "R-CMD-check") -> dict[str, Any]:
    started = datetime.fromisoformat(created.replace("Z", "+00:00"))
    return {
        "name": workflow,
        "conclusion": conclusion,
        "status": "completed",
        "created_at": created,
        "run_started_at": created,
        "updated_at": (started + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z"),
        "html_url": "https://github.com/example/example/actions/runs/1",
    }
