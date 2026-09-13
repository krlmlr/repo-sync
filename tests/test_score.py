"""The score: reasons that add up, weights that are configuration, and staleness carried through."""

import unittest
from copy import deepcopy

from portfolio import snapshot as snap
from portfolio.config import Config
from portfolio.score import score_entry, score_snapshot

from tests.support import FIXTURES, NOW, ago


class ScoreTest(unittest.TestCase):
    def test_contributions_account_for_the_total_in_every_fixture_entry(self):
        for name in ("snapshot.json", "snapshot_mirrors.json"):
            snapshot = snap.read(FIXTURES / name)
            for slug, entry in snapshot["packages"].items():
                with self.subTest(fixture=name, package=slug):
                    reasons = entry["score"]["reasons"]
                    self.assertEqual(entry["score"]["value"], round(sum(r["contribution"] for r in reasons), 2))

    def test_a_quiet_package_scores_zero_with_no_reasons(self):
        entry = {
            "ci": {"consecutive_failures": 0, "red_since": None, "latest_conclusion": "success"},
            "release": {"commits_by_type": {"chore": 2}},
            "cran": {"worst_status": "OK", "deadline": None},
            "tickets": {"issues_no_maintainer_reply": 0, "pull_requests_awaiting_review": 0},
            "template": {"collected": True, "outstanding": 0},
        }
        score = score_entry(entry, config=Config(), now=NOW)
        self.assertEqual(score["value"], 0)
        self.assertEqual(score["reasons"], [])

    def test_each_reason_appears_with_its_own_contribution(self):
        entry = {
            "ci": {"consecutive_failures": 2, "red_since": ago(10)},
            "cran": {"deadline": "2026-09-20"},
            "release": {"commits_by_type": {"feat": 2, "fix": 1}, "oldest_unreleased_at": ago(60)},
            "tickets": {"issues_no_maintainer_reply": 3, "pull_requests_awaiting_review": 1},
            "template": {"collected": True, "outstanding": 4},
        }
        score = score_entry(entry, config=Config(), now=NOW)
        codes = [reason["code"] for reason in score["reasons"]]
        self.assertEqual(
            codes, ["ci_red", "cran_deadline", "unreleased", "issues_no_reply", "prs_awaiting_review", "template_outstanding"]
        )
        for reason in score["reasons"]:
            self.assertGreater(reason["contribution"], 0)
            self.assertTrue(reason["label"])

    def test_an_uncollected_template_group_contributes_nothing(self):
        entry = {"template": {"collected": False, "reason": "no mirror"}}
        self.assertEqual(score_entry(entry, config=Config(), now=NOW)["value"], 0)

    def test_a_carried_forward_entry_carries_a_stale_score(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        stale = snapshot["packages"]["ghost/missing"]
        self.assertTrue(stale["stale"])
        self.assertTrue(stale["score"]["stale"])

    def test_changing_one_weight_changes_the_scores_and_nothing_else(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")
        before = deepcopy(snapshot)
        heavier = Config(weights=dict(Config().weights, ci_red_per_day=5.0))
        score_snapshot(snapshot, config=heavier, now=NOW)

        red = snapshot["packages"]["r-dbi/RKazam"]
        self.assertGreater(red["score"]["value"], before["packages"]["r-dbi/RKazam"]["score"]["value"])
        for slug, entry in snapshot["packages"].items():
            for group in snap.GROUPS:
                if group == "score":
                    continue
                with self.subTest(package=slug, group=group):
                    self.assertEqual(entry[group], before["packages"][slug][group])

    def test_the_ranking_moves_with_the_weights(self):
        snapshot = snap.read(FIXTURES / "snapshot.json")

        def ranking(config):
            copy = deepcopy(snapshot)
            score_snapshot(copy, config=config, now=NOW)
            return sorted(copy["packages"], key=lambda slug: -copy["packages"][slug]["score"]["value"])

        default = ranking(Config())
        issue_heavy = ranking(Config(weights=dict(Config().weights, issue_no_reply_per_issue=40.0, issue_no_reply_max=400.0)))
        self.assertNotEqual(default, issue_heavy)
        # A package whose only trouble is an unanswered issue overtakes one that is merely behind.
        self.assertLess(issue_heavy.index("krlmlr/notapackage"), issue_heavy.index("ghost/missing"))
        self.assertGreater(default.index("krlmlr/notapackage"), default.index("ghost/missing"))


if __name__ == "__main__":
    unittest.main()
