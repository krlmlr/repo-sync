"""The inventory is read the way the shell tools read it, and refused the same way."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio.inventory import InventoryError, load_inventory

from tests.support import FIXTURES


class InventoryTest(unittest.TestCase):
    def write(self, text: str) -> Path:
        directory = Path(self.enterContext(TemporaryDirectory()))
        path = directory / "repos.yml"
        path.write_text(text)
        return path

    def test_inventory_order_is_file_order(self):
        inventory = load_inventory(FIXTURES / "repos.yml")
        self.assertEqual([entry.slug for entry in inventory][0], "cynkra/cynkratemplate")
        self.assertEqual(len(inventory), 7)

    def test_no_template_is_refused(self):
        path = self.write("repos:\n  - org: a\n    repo: b\n")
        with self.assertRaises(InventoryError) as caught:
            load_inventory(path)
        self.assertIn("template: true", str(caught.exception))

    def test_two_templates_are_refused(self):
        path = self.write(
            "repos:\n  - org: a\n    repo: b\n    template: true\n  - org: c\n    repo: d\n    template: true\n"
        )
        with self.assertRaises(InventoryError) as caught:
            load_inventory(path)
        self.assertIn("multiple", str(caught.exception))

    def test_the_real_inventory_loads(self):
        inventory = load_inventory(Path(__file__).resolve().parents[1] / "repos.yml")
        self.assertEqual(inventory.template_slug, "cynkra/cynkratemplate")
        self.assertGreater(len(inventory), 40)


if __name__ == "__main__":
    unittest.main()
