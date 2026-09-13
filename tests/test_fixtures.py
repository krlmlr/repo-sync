"""The committed fixtures are the ones the collector produces, and not a hand-made approximation."""

import unittest

from portfolio import snapshot as snap

from tests import make_fixtures
from tests.support import FIXTURES


class FixturesTest(unittest.TestCase):
    def test_the_committed_fixtures_match_what_the_generator_produces(self):
        previous = make_fixtures.collect_fixture()
        self.assertEqual(snap.dumps(previous), (FIXTURES / "snapshot_previous.json").read_text())

        current = make_fixtures.collect_fixture(missing=("ghost/missing",), previous=previous)
        self.assertEqual(snap.dumps(current), (FIXTURES / "snapshot.json").read_text())
        self.assertEqual(
            snap.dumps(make_fixtures.with_mirror_groups(current)), (FIXTURES / "snapshot_mirrors.json").read_text()
        )
        self.assertEqual(snap.dumps(make_fixtures.cleared(current)), (FIXTURES / "snapshot_clear.json").read_text())

    def test_the_fixtures_cover_every_shape_the_renderer_must_handle(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        packages = snapshot["packages"]
        self.assertFalse(packages["tidyverse/tibble"]["stale"])
        self.assertTrue(packages["ghost/missing"]["stale"])
        self.assertTrue(packages["ghost/never"]["never_observed"])
        self.assertFalse(packages["krlmlr/notapackage"]["identity"]["is_r_package"])
        self.assertIsNone(packages["krlmlr/bindr"]["ci"]["latest_conclusion"])
        self.assertIsNone(packages["krlmlr/notapackage"]["release"]["latest_tag"])
        self.assertTrue(packages["krlmlr/bindr"]["identity"]["archived"])
        self.assertTrue(packages["krlmlr/bindr"]["activity"]["dormant"])
        self.assertEqual(packages["r-dbi/RKazam"]["cran"]["deadline"], "2026-09-20")
        self.assertEqual(snapshot["groups_collected"], {"template": False, "workspace": False})

        mirrored = snap.read(FIXTURES / "snapshot_mirrors.json")
        self.assertEqual(mirrored["groups_collected"], {"template": True, "workspace": True})
        self.assertTrue(mirrored["packages"]["r-dbi/RKazam"]["workspace"]["dirty"])

        clear = snap.read(FIXTURES / "snapshot_clear.json")
        self.assertTrue(all(entry["score"]["value"] == 0 for entry in clear["packages"].values()))


if __name__ == "__main__":
    unittest.main()
