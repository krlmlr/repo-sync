"""The snapshot, formatted.

A pure function of one document: no network, no clock, no inventory. The same snapshot renders the
same bytes, which is what lets the page be iterated on against a fixture instead of against
forty-six live repositories, and what makes "publish only when the output changed" mean something.

Two modes, one page. Locally the snapshot is inlined, because `fetch` of a neighbouring file is
blocked under `file://` and a local page that cannot read its own data is not a local page. On
publication it is not, because the page and the document are both published and the page picking
up a new collection on reload is the whole point of it being a client.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import snapshot as snap

ASSETS = Path(__file__).resolve().parent / "assets"


def _asset(name: str) -> str:
    return (ASSETS / name).read_text()


def embed_json(snapshot: dict[str, Any]) -> str:
    """The snapshot as it goes inside a `<script>` element.

    `<` is escaped because a description containing `</script>` would otherwise end the element and
    the page with it. `\\u003c` is the same string to any JSON parser and inert to the HTML one.
    """
    return json.dumps(snapshot, ensure_ascii=False).replace("<", "\\u003c")


def render_page(snapshot: dict[str, Any] | None) -> str:
    """The page, with the snapshot inlined when one is given and fetched when it is not."""
    template = _asset("page.html")
    return (
        template.replace("{{STYLE}}", _asset("page.css"))
        .replace("{{SCRIPT}}", _asset("page.js"))
        .replace("{{DATA}}", embed_json(snapshot) if snapshot is not None else "")
    )


def write_local(snapshot: dict[str, Any], out_dir: Path) -> Path:
    """One file that works on a double-click."""
    out_dir.mkdir(parents=True, exist_ok=True)
    page = out_dir / "index.html"
    page.write_text(render_page(snapshot))
    return page


def write_published(snapshot: dict[str, Any], out_dir: Path) -> list[Path]:
    """The page, the document it reads, and the history the trend is made of.

    The local groups are stripped here rather than by the caller, so that publication cannot happen
    without it having happened.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    published = snap.strip_local_groups(snapshot)

    page = out_dir / "index.html"
    page.write_text(render_page(None))
    document = out_dir / "metrics.json"
    document.write_text(snap.dumps(published))

    written = [page, document]
    collected_at = published.get("collected_at") or "unknown"
    retained = out_dir / "history" / f"{collected_at.replace(':', '')}.json"
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_text(snap.dumps(published))
    written.append(retained)

    counters = published.get("portfolio") or snap.portfolio_counters(published)
    series = out_dir / "history.jsonl"
    lines = [line for line in series.read_text().splitlines() if line.strip()] if series.exists() else []
    # One line per reading, not per run: republishing the same collection replaces its line rather
    # than adding a second one that would draw the same day twice in the trend.
    lines = [line for line in lines if json.loads(line).get("collected_at") != collected_at]
    lines.append(json.dumps(counters, ensure_ascii=False))
    series.write_text("\n".join(lines) + "\n")
    written.append(series)
    return written
