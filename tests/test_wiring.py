"""The wiring: the tasks, the ignores, the dependency that was not added, and the workflow."""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class TasksTest(unittest.TestCase):
    def setUp(self):
        self.mise = tomllib.loads((ROOT / "mise.toml").read_text())

    def test_each_new_script_has_a_named_task(self):
        expected = {
            "metrics": "scripts/collect_metrics.py",
            "dashboard": "scripts/render_dashboard.py",
            "publish-dashboard": "scripts/publish_dashboard.sh",
        }
        for task, script in expected.items():
            with self.subTest(task=task):
                self.assertIn(task, self.mise["tasks"])
                self.assertIn(script, self.mise["tasks"][task]["run"])
                self.assertTrue(self.mise["tasks"][task]["description"])
                self.assertTrue((ROOT / script).exists())

    def test_the_suite_has_one_too(self):
        self.assertIn("unittest discover", self.mise["tasks"]["test"]["run"])

    def test_the_existing_tasks_are_untouched(self):
        self.assertEqual(self.mise["tasks"]["clone"]["run"], "bash scripts/clone.sh")
        self.assertEqual(self.mise["tasks"]["sync"]["run"], "bash scripts/sync.sh")

    def test_the_prerequisites_are_documented_where_the_others_are(self):
        text = (ROOT / "mise.toml").read_text()
        block = text.split("[tasks.metrics]")[0].split("[tasks.sync]")[1]
        for mention in ("GITHUB_TOKEN", "gh auth token", "CRAN", "mirrors/", "parallel"):
            self.assertIn(mention, block)


class IgnoresTest(unittest.TestCase):
    def test_generated_output_is_ignored(self):
        ignores = (ROOT / ".gitignore").read_text().split()
        self.assertIn("/reports/", ignores)
        self.assertIn("/mirrors/", ignores)
        self.assertIn("__pycache__/", ignores)


class DependencyTest(unittest.TestCase):
    def test_no_http_client_was_added(self):
        """`urllib.request` does the job, so `requirements.txt` gains nothing.

        The collector makes plain JSON requests with a bearer token, which `urlopen` does; a
        dependency to install, pin and update would buy nothing that a portfolio reading needs.
        """
        requirements = [
            line.strip()
            for line in (ROOT / "requirements.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertEqual(requirements, ["PyYAML==6.0.2"])

    def test_no_http_library_is_imported_anywhere(self):
        for module in sorted((ROOT / "scripts" / "portfolio").glob("*.py")):
            imports = set(re.findall(r"^(?:from|import)\s+([a-zA-Z_][\w.]*)", module.read_text(), re.MULTILINE))
            third_party = imports & {"requests", "httpx", "urllib3", "aiohttp"}
            with self.subTest(module=module.name):
                self.assertFalse(third_party, f"{module.name} imports {third_party}")


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / ".github" / "workflows" / "dashboard.yaml"
        self.raw = self.path.read_text()
        self.workflow = yaml.safe_load(self.raw)
        # PyYAML reads the `on:` key as the boolean True, which is YAML 1.1 doing as it is told.
        self.triggers = self.workflow[True] if True in self.workflow else self.workflow["on"]

    def test_it_runs_on_a_schedule_and_on_demand(self):
        self.assertIn("schedule", self.triggers)
        self.assertIn("workflow_dispatch", self.triggers)
        self.assertTrue(self.triggers["schedule"][0]["cron"])

    def test_it_reads_the_token_actions_mints_and_stores_no_secret_of_its_own(self):
        secrets = set(re.findall(r"secrets\.([A-Za-z_]+)", self.raw))
        self.assertEqual(secrets, {"GITHUB_TOKEN"})
        self.assertEqual(self.workflow["permissions"], {"contents": "write"})

    def test_it_publishes_even_when_some_packages_could_not_be_read(self):
        steps = self.workflow["jobs"]["publish"]["steps"]
        collect = next(step for step in steps if step.get("id") == "collect")
        self.assertTrue(collect["continue-on-error"])
        self.assertIn("scripts/collect_metrics.py", collect["run"])
        publish = next(step for step in steps if "publish_dashboard.sh" in str(step.get("run", "")))
        self.assertGreater(steps.index(publish), steps.index(collect))
        # And the run still ends non-zero, because the exit status is for whoever watches the schedule.
        final = steps[-1]
        self.assertIn("steps.collect.outcome == 'failure'", final["if"])
        self.assertIn("exit 1", final["run"])

    def test_disabling_it_affects_nothing_local(self):
        for script in ("collect_metrics.py", "render_dashboard.py", "publish_dashboard.sh"):
            with self.subTest(script=script):
                self.assertNotIn("workflows", (ROOT / "scripts" / script).read_text())


if __name__ == "__main__":
    unittest.main()
