"""The field reference documents the fields, and the credential note matches the workflow."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests.support import FIXTURES

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "dashboard.md"


def field_names(value, found: set[str]) -> set[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            found.add(key)
            field_names(nested, found)
    elif isinstance(value, list):
        for item in value:
            field_names(item, found)
    return found


class FieldReferenceTest(unittest.TestCase):
    def test_every_field_in_the_fixture_is_documented(self):
        text = DOCS.read_text()
        documented = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", text))
        snapshot = json.loads((FIXTURES / "snapshot_mirrors.json").read_text())
        present = field_names(snapshot, set())
        # Slugs and Conventional Commits types are values, not fields: they are keys because the
        # document is keyed by them, and the reference says so rather than listing every one.
        values = set(snapshot["packages"]) | {"feat", "fix", "docs", "chore", "ci", "unclassified"}
        undocumented = sorted(present - documented - values)
        self.assertEqual(undocumented, [], f"fields missing from {DOCS.name}: {undocumented}")

    def test_the_add_or_deprecate_rule_is_stated(self):
        text = DOCS.read_text()
        self.assertIn("added or deprecated, never repurposed", text)


class CredentialNoteTest(unittest.TestCase):
    def test_the_note_says_why_a_credential_is_required(self):
        text = DOCS.read_text()
        self.assertIn("refuses anonymous requests", text)
        self.assertIn("GITHUB_TOKEN", text)
        self.assertIn("gh auth token", text)

    def test_the_note_lists_what_declining_a_stored_token_costs(self):
        text = DOCS.read_text().lower()
        for cost in ("draft releases", "maintainer identification", "private entries", "headroom"):
            self.assertIn(cost, text)

    def test_the_note_matches_what_the_workflow_actually_does(self):
        workflow = (ROOT / ".github" / "workflows" / "dashboard.yaml").read_text()
        self.assertIn("secrets.GITHUB_TOKEN", workflow)
        self.assertEqual(len(set(re.findall(r"secrets\.([A-Za-z_]+)", workflow))), 1)
        self.assertIn("dashboard.yaml", DOCS.read_text())


if __name__ == "__main__":
    unittest.main()
