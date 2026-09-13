"""Read `repos.yml` the way the shell tools read it.

`scripts/lib.sh` holds the template designation for `clone` and `sync`, and this is the same
rule in the language the collector is written in: exactly one entry carries `template: true`,
zero or several is a malformed inventory, and a malformed inventory is rejected before any
work starts rather than half way through it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class InventoryError(Exception):
    """A `repos.yml` that cannot be used, reported rather than worked around."""


@dataclass(frozen=True)
class Entry:
    org: str
    repo: str
    is_template: bool = False

    @property
    def slug(self) -> str:
        return f"{self.org}/{self.repo}"


@dataclass(frozen=True)
class Inventory:
    entries: tuple[Entry, ...]
    template_slug: str

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


def load_inventory(path: Path) -> Inventory:
    """Parse the inventory, in file order, with the template designation validated."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError as exc:
        raise InventoryError(f"no repository inventory at {path}") from exc
    except yaml.YAMLError as exc:
        raise InventoryError(f"unable to parse {path}: {exc}") from exc

    raw = data.get("repos")
    if not raw:
        raise InventoryError(f"{path} lists no repositories")

    entries = []
    for item in raw:
        try:
            org, repo = item["org"], item["repo"]
        except (TypeError, KeyError) as exc:
            raise InventoryError(f"{path} has an entry without org and repo: {item!r}") from exc
        entries.append(Entry(org=org, repo=repo, is_template=item.get("template") is True))

    flagged = [e for e in entries if e.is_template]
    if not flagged:
        raise InventoryError(f"no entry in {path.name} has template: true")
    if len(flagged) > 1:
        named = ", ".join(e.slug for e in flagged)
        raise InventoryError(f"multiple entries in {path.name} have template: true: {named}")

    return Inventory(entries=tuple(entries), template_slug=flagged[0].slug)
