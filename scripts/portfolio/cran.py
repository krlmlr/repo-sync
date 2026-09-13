"""What CRAN says about a package.

Two pages, both confirmed against the live service during implementation -- see `design.md`:

- `web/packages/<pkg>/DESCRIPTION` for the version CRAN serves and the date it published it.
  It is the same format the repository's own `DESCRIPTION` is in, so it is read by the same parser.
- `web/checks/check_results_<pkg>.html` for the status per flavour and for a deadline when CRAN
  has set one. There is no contractually stable machine-readable equivalent: the per-flavour
  `.rds` tables carry no deadline column, so this page is the only source that carries both.

The page is HTML that CRAN generates, so parsing it is a bet on its shape. That is why the whole
group degrades to unavailable rather than failing the run: no metric outside it depends on CRAN,
and a portfolio reading missing one group beats no portfolio reading.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from .dcf import parse_dcf
from .transport import Client, Unreadable

CRAN_ROOT = "https://cran.r-project.org"

# Worst first, which is the order the page ranks a package's flavours by.
STATUS_ORDER = ("ERROR", "FAIL", "WARN", "NOTE", "OK")
DEADLINE = re.compile(r"Deadline:\s*(\d{4}-\d{2}-\d{2})")
LAST_UPDATED = re.compile(r"Last updated on\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")


class _CheckTableParser(HTMLParser):
    """The first table on a check-results page, as rows of cell text.

    An HTML parser rather than a regular expression over tags: the cells carry nested `<a>` and
    `<span>`, and a pattern that copes with those is a parser written badly.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._in_table = False
        self._done = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and not self._done:
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "table" and self._in_table:
            self._in_table = False
            self._done = True

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_check_results(html: str) -> dict[str, Any]:
    """Flavour rows, the counts across them, the worst of them, and a deadline if CRAN set one."""
    parser = _CheckTableParser()
    parser.feed(html)
    flavours = []
    for row in parser.rows:
        if len(row) < 6 or not row[0] or row[0].lower() == "flavor":
            continue
        status = row[5].strip().upper()
        if status not in STATUS_ORDER:
            continue
        flavours.append({"flavour": row[0], "version": row[1] or None, "status": status})

    counts: dict[str, int] = {}
    for flavour in flavours:
        counts[flavour["status"]] = counts.get(flavour["status"], 0) + 1
    worst = next((status for status in STATUS_ORDER if status in counts), None)
    deadline = DEADLINE.search(html)
    updated = LAST_UPDATED.search(html)
    return {
        "flavours": flavours,
        "status_counts": {status: counts[status] for status in STATUS_ORDER if status in counts},
        "worst_status": worst,
        "deadline": deadline.group(1) if deadline else None,
        "checked_at": updated.group(1) if updated else None,
    }


class CranSource:
    """The two requests a package costs, and the three states an answer can be in.

    `available` is a reading; `absent` is a package CRAN does not have, which is a fact about the
    package; `unavailable` is CRAN not answering, which is a fact about the run.
    """

    def __init__(self, client: Client):
        self.client = client

    def _get(self, url: str) -> tuple[int, str]:
        response = self.client.request(
            "GET", url, kind="cran", headers={"User-Agent": "repo-sync-dashboard", "Accept": "text/html"}
        )
        return response.status, response.text()

    def package(self, name: str) -> dict[str, Any]:
        group: dict[str, Any] = {
            "state": "unavailable",
            "package": name,
            "version": None,
            "published_at": None,
            "flavours": [],
            "status_counts": {},
            "worst_status": None,
            "deadline": None,
            "checked_at": None,
            "package_url": f"{CRAN_ROOT}/package={name}",
            "checks_url": f"{CRAN_ROOT}/web/checks/check_results_{name}.html",
        }
        try:
            status, text = self._get(f"{CRAN_ROOT}/web/packages/{name}/DESCRIPTION")
        except Unreadable:
            return group
        if status == 404:
            # Not on CRAN: a package that was never published, or one that has been archived.
            return dict(group, state="absent")
        if status != 200:
            return group

        fields = parse_dcf(text)
        group["version"] = fields.get("Version")
        published = fields.get("Date/Publication")
        group["published_at"] = published.split(" ")[0] if published else None

        try:
            status, html = self._get(group["checks_url"])
        except Unreadable:
            return dict(group, state="unavailable")
        if status != 200:
            # A version on CRAN with no check page is still a reading, just a thinner one.
            return dict(group, state="available")
        parsed = parse_check_results(html)
        if not parsed["flavours"]:
            return dict(group, state="unavailable")
        group.update(parsed)
        group["state"] = "available"
        return group
