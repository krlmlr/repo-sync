"""One run, end to end, with the network replaced by recorded answers.

This is where the discipline the shell tools set is checked: failure is per package, a package that
cannot be read costs a stale row rather than the run, the failures are named at the end, and the
exit status is non-zero while the snapshot is written regardless.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portfolio import snapshot as snap
from portfolio.collect import collect, report
from portfolio.config import Config
from portfolio.cran import CranSource
from portfolio.github import GitHubSource
from portfolio.inventory import load_inventory
from portfolio.transport import Client, Response, Transport

from tests import make_fixtures
from tests.support import FIXTURES, NOW, FakeTransport
from tests.test_mirrors import ENV, commit, git


class LimitedTransport(Transport):
    """A remote that asks to be left alone, and then relents after `until` refusals."""

    def __init__(self, inner: Transport, *, until: int | None):
        self.inner = inner
        self.until = until
        self.refusals = 0

    def request(self, method, url, *, headers=None, body=None):
        if self.until is None or self.refusals < self.until:
            self.refusals += 1
            return Response(403, {"Retry-After": "1"}, b"You have exceeded a secondary rate limit")
        return self.inner.request(method, url, headers=headers, body=body)


def run_collect(*, transport=None, mirrors: Path | None = None, previous=None, repos: Path | None = None, config=None):
    settings = config or make_fixtures.config()
    inventory = load_inventory(repos or FIXTURES / "repos.yml")
    transport = transport or FakeTransport(
        repos=make_fixtures.repositories(), runs=make_fixtures.runs(), cran=make_fixtures.cran()
    )
    client = Client(transport=transport, sleep=lambda _: None)
    result = collect(
        inventory=inventory,
        config=settings,
        github=GitHubSource(client, "token", settings, now=NOW),
        cran=CranSource(client),
        mirrors_dir=mirrors or FIXTURES / "no-mirrors",
        previous=previous,
        now=NOW,
        log=lambda message: None,
    )
    return result, client


class InventoryShapeTest(unittest.TestCase):
    def test_one_entry_per_inventory_entry_in_inventory_order(self):
        inventory = load_inventory(FIXTURES / "repos.yml")
        result, _ = run_collect()
        self.assertEqual(len(result["packages"]), len(inventory))
        self.assertEqual(list(result["packages"]), [entry.slug for entry in inventory])

    def test_two_runs_produce_the_same_order_and_the_same_document(self):
        first, _ = run_collect()
        second, _ = run_collect()
        self.assertEqual(snap.dumps(first), snap.dumps(second))


class BudgetTest(unittest.TestCase):
    def test_the_facts_are_batched_and_the_count_is_reported(self):
        result, client = run_collect()
        # Seven repositories, three per query: the facts cost three requests rather than seven,
        # and far less than one request per metric per package.
        self.assertEqual(client.counts["graphql"], 3)
        self.assertEqual(result["requests"]["graphql"], 3)
        self.assertEqual(result["requests"]["total"], client.total)

    def test_the_real_inventory_batches_into_five_queries(self):
        """The shape of the budget against the real inventory, with recorded answers.

        Not a measurement of the live service -- nothing here reaches GitHub -- but the request
        count is a property of the batching, and this is the inventory it will be run against.
        """
        repos = Path(__file__).resolve().parents[1] / "repos.yml"
        inventory = load_inventory(repos)
        transport = FakeTransport(repos={}, runs={}, cran={})
        result, client = run_collect(transport=transport, repos=repos, config=Config())
        self.assertEqual(len(result["packages"]), len(inventory))
        self.assertEqual(client.counts["graphql"], 5)
        self.assertLess(client.total, 200)


class ResilienceTest(unittest.TestCase):
    def test_one_unreadable_repository_costs_one_stale_row(self):
        previous = snap.read(FIXTURES / "snapshot_previous.json")
        result, _ = run_collect(
            transport=FakeTransport(
                repos={slug: node for slug, node in make_fixtures.repositories().items() if slug != "ghost/missing"},
                runs=make_fixtures.runs(),
                cran=make_fixtures.cran(),
            ),
            previous=previous,
        )
        stale = result["packages"]["ghost/missing"]
        self.assertTrue(stale["stale"])
        self.assertFalse(stale["never_observed"])
        self.assertEqual(stale["observed_at"], previous["packages"]["ghost/missing"]["observed_at"])
        self.assertEqual(stale["identity"]["package"], "ghostly")
        self.assertFalse(result["packages"]["tidyverse/tibble"]["stale"])
        self.assertIn("ghost/missing", result["failures"])
        self.assertEqual(report(result, log=lambda message: None), 1)

    def test_a_package_with_no_previous_reading_is_never_observed(self):
        result, _ = run_collect()
        never = result["packages"]["ghost/never"]
        self.assertTrue(never["never_observed"])
        self.assertIsNone(never["observed_at"])
        self.assertIsNone(never["tickets"])
        # Distinguishable from a measured zero, which is the whole point of the flag.
        self.assertIsNotNone(result["packages"]["cynkra/cynkratemplate"]["tickets"]["open_issues"])

    def test_a_run_where_everything_fails_still_writes_a_snapshot(self):
        result, _ = run_collect(transport=FakeTransport(repos={}, runs={}, cran={}))
        directory = Path(self.enterContext(TemporaryDirectory()))
        snap.write(result, directory / "metrics.json")
        self.assertTrue((directory / "metrics.json").exists())
        self.assertTrue(all(entry["stale"] for entry in result["packages"].values()))
        self.assertEqual(len(result["failures"]), len(result["packages"]))
        self.assertEqual(report(result, log=lambda message: None), 1)

    def test_a_rate_limit_is_waited_out_rather_than_raised(self):
        inner = FakeTransport(repos=make_fixtures.repositories(), runs=make_fixtures.runs(), cran=make_fixtures.cran())
        result, _ = run_collect(transport=LimitedTransport(inner, until=2))
        self.assertFalse(result["packages"]["tidyverse/tibble"]["stale"])
        self.assertEqual(result["failures"], ["ghost/never"])

    def test_a_rate_limit_that_never_lifts_records_the_packages_unreadable(self):
        inner = FakeTransport(repos=make_fixtures.repositories(), runs=make_fixtures.runs(), cran=make_fixtures.cran())
        result, _ = run_collect(transport=LimitedTransport(inner, until=None))
        self.assertTrue(all(entry["stale"] for entry in result["packages"].values()))
        self.assertEqual(report(result, log=lambda message: None), 1)

    def test_the_report_names_the_failures_and_the_request_count(self):
        result, _ = run_collect()
        lines: list[str] = []
        status = report(result, log=lines.append)
        self.assertEqual(status, 1)
        self.assertTrue(any(line.startswith("\nREQUESTS (") for line in lines))
        self.assertTrue(any(line.startswith("FAILED (1): ghost/never") for line in lines))

    def test_cran_being_unreachable_costs_the_cran_group_and_nothing_else(self):
        transport = FakeTransport(
            repos=make_fixtures.repositories(), runs=make_fixtures.runs(), cran=make_fixtures.cran(), cran_down=True
        )
        result, _ = run_collect(transport=transport)
        tibble = result["packages"]["tidyverse/tibble"]
        self.assertEqual(tibble["cran"]["state"], "unavailable")
        self.assertIsNotNone(tibble["ci"]["latest_conclusion"])
        self.assertIsNotNone(tibble["tickets"]["open_issues"])
        self.assertIsNotNone(tibble["release"]["latest_tag"])
        self.assertNotIn("tidyverse/tibble", result["failures"])


class CranPositionTest(unittest.TestCase):
    def test_a_development_version_ahead_of_cran_records_both(self):
        result, _ = run_collect()
        release = result["packages"]["tidyverse/tibble"]["release"]
        self.assertEqual(release["cran_version"], "3.3.1")
        self.assertEqual(release["cran_published_at"], "2026-01-11")
        self.assertEqual(result["packages"]["tidyverse/tibble"]["identity"]["version"], "3.3.1.9000")
        self.assertTrue(release["ahead_of_cran"])

    def test_a_package_level_of_cran_is_recorded_across_flavours(self):
        result, _ = run_collect()
        cran = result["packages"]["tidyverse/tibble"]["cran"]
        self.assertEqual(cran["state"], "available")
        self.assertEqual(cran["worst_status"], "NOTE")
        self.assertEqual(len(cran["flavours"]), 13)
        self.assertEqual(result["packages"]["r-dbi/RKazam"]["cran"]["deadline"], "2026-09-20")


class MirrorGroupsTest(unittest.TestCase):
    def test_a_machine_with_no_mirrors_omits_both_groups_and_exits_zero(self):
        result, _ = run_collect(mirrors=Path("/nonexistent/mirrors"))
        self.assertEqual(result["groups_collected"], {"template": False, "workspace": False})
        for entry in result["packages"].values():
            self.assertIsNone(entry["template"])
            self.assertIsNone(entry["workspace"])
        # The one ghost fails for want of a credentialed answer, not for want of mirrors.
        self.assertEqual(result["failures"], ["ghost/never"])

    def test_a_run_with_no_mirrors_and_nothing_unreadable_exits_zero(self):
        every_repository = dict(make_fixtures.repositories())
        # The one entry the fixtures deliberately never record, given a payload so that this run
        # has nothing to fail on: what is under test is the absence of mirrors, not a failure.
        from tests.support import repository

        every_repository["ghost/never"] = repository("ghost/never", releases=[], commits=[])
        result, _ = run_collect(
            transport=FakeTransport(repos=every_repository, runs=make_fixtures.runs(), cran=make_fixtures.cran()),
            mirrors=Path("/nonexistent/mirrors"),
        )
        self.assertEqual(result["failures"], [])
        self.assertEqual(report(result, log=lambda message: None), 0)
        self.assertEqual(result["groups_collected"], {"template": False, "workspace": False})
        self.assertTrue(all(entry["template"] is None for entry in result["packages"].values()))

    def test_one_missing_mirror_is_uncollected_while_the_others_carry_theirs(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        mirrors = self.build_mirrors(root)
        result, _ = run_collect(mirrors=mirrors)
        self.assertEqual(result["groups_collected"], {"template": True, "workspace": True})
        tibble = result["packages"]["tidyverse/tibble"]
        self.assertTrue(tibble["template"]["collected"])
        self.assertEqual(tibble["template"]["outstanding"], 2)
        self.assertFalse(tibble["workspace"]["dirty"])
        absent = result["packages"]["krlmlr/bindr"]
        self.assertFalse(absent["template"]["collected"])
        self.assertIn("no mirror", absent["template"]["reason"])
        template = result["packages"]["cynkra/cynkratemplate"]
        self.assertFalse(template["template"]["collected"])
        self.assertIn("itself", template["template"]["reason"])

    def build_mirrors(self, root: Path) -> Path:
        mirrors = root / "mirrors"
        template = mirrors / "cynkra" / "cynkratemplate"
        template.mkdir(parents=True)
        git(template, "init", "-b", "main")
        commit(template, "a.txt", "a\n", "feat: template one", "2026-01-01T00:00:00Z")
        commit(template, "b.txt", "b\n", "feat: template two", "2026-02-01T00:00:00Z")
        import subprocess

        subprocess.run(
            ["git", "clone", "--mirror", str(template), str(mirrors / "cynkra" / "cynkratemplate.git")],
            capture_output=True,
            env=ENV,
            check=True,
        )
        mirror = mirrors / "tidyverse" / "tibble"
        mirror.mkdir(parents=True)
        git(mirror, "init", "-b", "main")
        commit(mirror, "own.txt", "own\n", "chore: own work", "2025-06-01T00:00:00Z")
        git(mirror, "remote", "add", "template", "../../cynkra/cynkratemplate.git")
        git(mirror, "fetch", "--no-tags", "template")
        return mirrors


class OffTheCriticalPathTest(unittest.TestCase):
    def test_neither_clone_nor_sync_knows_this_exists(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for name in ("clone.sh", "sync.sh", "lib.sh"):
            text = (scripts / name).read_text()
            with self.subTest(script=name):
                for mention in ("collect_metrics", "render_dashboard", "portfolio", "metrics.json"):
                    self.assertNotIn(mention, text)

    def test_the_shell_tools_still_parse(self):
        import subprocess

        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for name in ("clone.sh", "sync.sh"):
            with self.subTest(script=name):
                self.assertEqual(subprocess.run(["bash", "-n", str(scripts / name)]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
