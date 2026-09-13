"""The snapshot contract: what is written, what round-trips, and what publication removes."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio import snapshot as snap

from tests.support import FIXTURES


class SnapshotTest(unittest.TestCase):
    def test_round_trip_carries_the_top_level_fields(self):
        written = snap.new_snapshot(template_slug="a/b", groups_collected={"template": False, "workspace": False})
        written["packages"]["a/b"] = snap.new_entry("a/b", "a", "b", is_template=True)
        directory = Path(self.enterContext(TemporaryDirectory()))
        snap.write(written, directory / "metrics.json")
        read_back = snap.read(directory / "metrics.json")
        self.assertEqual(read_back, written)
        self.assertEqual(read_back["schema_version"], snap.SCHEMA_VERSION)
        self.assertTrue(read_back["collected_at"])

    def test_every_group_is_present_on_a_new_entry(self):
        entry = snap.new_entry("a/b", "a", "b")
        for group in snap.GROUPS:
            self.assertIn(group, entry)

    def test_a_snapshot_from_another_schema_is_not_read(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        path = directory / "metrics.json"
        path.write_text(json.dumps({"schema_version": snap.SCHEMA_VERSION + 1, "packages": {}}))
        self.assertIsNone(snap.read(path))

    def test_publication_strips_the_local_group_by_name(self):
        snapshot = snap.read(FIXTURES / "snapshot_mirrors.json")
        # A field nobody has thought of yet, added to the group after the fact.
        snapshot["packages"]["r-dbi/RKazam"]["workspace"]["secret_branch_name"] = "wip/embarrassing"
        published = snap.strip_local_groups(snapshot)
        self.assertNotIn("workspace", published["groups"])
        for entry in published["packages"].values():
            self.assertNotIn("workspace", entry)
        self.assertNotIn("embarrassing", snap.dumps(published))

    def test_publication_keeps_the_template_group(self):
        snapshot = snap.read(FIXTURES / "snapshot_mirrors.json")
        published = snap.strip_local_groups(snapshot)
        self.assertIn("template", published["groups"])
        self.assertTrue(published["packages"]["tidyverse/tibble"]["template"]["collected"])

    def test_carry_forward_marks_stale_and_keeps_values(self):
        previous = snap.new_entry("a/b", "a", "b")
        previous["identity"] = {"package": "b"}
        previous["observed_at"] = "2026-01-01T00:00:00Z"
        carried = snap.carry_forward(previous, snap.new_entry("a/b", "a", "b"), "unreadable")
        self.assertTrue(carried["stale"])
        self.assertFalse(carried["never_observed"])
        self.assertEqual(carried["identity"], {"package": "b"})
        self.assertEqual(carried["observed_at"], "2026-01-01T00:00:00Z")

    def test_carry_forward_with_no_previous_is_never_observed(self):
        carried = snap.carry_forward(None, snap.new_entry("a/b", "a", "b"), "unreadable")
        self.assertTrue(carried["never_observed"])
        self.assertIsNone(carried["observed_at"])
        self.assertIsNone(carried["identity"])


if __name__ == "__main__":
    unittest.main()
