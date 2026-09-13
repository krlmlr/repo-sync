"""The rendered page: deterministic, self-contained, and the behaviour its JavaScript promises."""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio import snapshot as snap
from portfolio.render import render_page, write_local, write_published

from tests.support import FIXTURES

ROOT = Path(__file__).resolve().parents[1]


class RenderTest(unittest.TestCase):
    def test_the_same_snapshot_renders_the_same_bytes(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        self.assertEqual(render_page(snapshot), render_page(snapshot))

    def test_rendering_needs_no_network(self):
        """There is nothing to stub: the renderer imports no transport and takes a file.

        The check is structural on purpose -- a renderer that could reach the network would have to
        import something that can, and this is the assertion that it does not.
        """
        text = (ROOT / "scripts" / "portfolio" / "render.py").read_text()
        for forbidden in ("urllib", "transport", "requests", "socket"):
            self.assertNotIn(forbidden, text)

    def test_the_local_page_carries_the_reading_and_the_published_one_does_not(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        directory = Path(self.enterContext(TemporaryDirectory()))
        local = write_local(snapshot, directory / "local").read_text()
        self.assertIn('id="snapshot-data">{"schema_version"', local)

        published_dir = directory / "published"
        write_published(snapshot, published_dir)
        published = (published_dir / "index.html").read_text()
        self.assertIn('id="snapshot-data"></script>', published)
        self.assertTrue((published_dir / "metrics.json").exists())

    def test_a_description_that_ends_a_script_element_cannot(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        snapshot["packages"]["tidyverse/tibble"]["identity"]["description"] = "</script><script>alert(1)</script>"
        page = render_page(snapshot)
        self.assertNotIn("</script><script>alert(1)", page)
        self.assertIn("\\u003c/script>", page)

    def test_the_page_fetches_nothing_from_anywhere_else(self):
        page = render_page(snap.read(FIXTURES / "snapshot.json"))
        for asset in ("<script src=", "<link rel=\"stylesheet\"", "@import", "url(http"):
            self.assertNotIn(asset, page)
        # The only absolute URLs are the ones a reader clicks, and they are anchors.
        for line in page.splitlines():
            if "https://" in line and "href=" not in line and "url:" not in line:
                self.assertNotIn("src=", line)

    def test_the_table_scrolls_rather_than_the_document(self):
        page = render_page(snap.read(FIXTURES / "snapshot.json"))
        self.assertIn('<div class="scroll"><table id="table">', page)
        self.assertIn(".scroll { overflow-x: auto;", page)
        self.assertIn('name="viewport"', page)
        # Nothing may demand a width a phone does not have: the table scrolls inside its container,
        # and every other element fits or wraps.
        widths = re.findall(r"min-width:\s*([0-9.]+)(rem|px)", page)
        for value, unit in widths:
            limit = 18.0 if unit == "rem" else 288.0
            self.assertLessEqual(float(value), limit, f"min-width: {value}{unit} is wider than a phone")


@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class PageBehaviourTest(unittest.TestCase):
    def test_the_page_behaves_as_specified_against_the_fixtures(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "page_harness.js"), str(ROOT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
