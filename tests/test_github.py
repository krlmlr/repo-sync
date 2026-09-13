"""The GitHub derivations, against recorded payloads rather than against the network."""

import unittest

from portfolio.config import Config
from portfolio.github import (
    GitHubSource,
    activity_group,
    build_query,
    ci_group,
    classify_subjects,
    identity_group,
    release_group,
    run_entry,
    tickets_group,
)
from portfolio.transport import Client

from tests.support import NOW, FakeTransport, ago, issue, pull_request, repository, run


def source(transport: FakeTransport, config: Config | None = None) -> GitHubSource:
    return GitHubSource(Client(transport=transport, sleep=lambda _: None), "token", config or Config(), now=NOW)


class QueryTest(unittest.TestCase):
    def test_one_query_carries_many_repositories(self):
        query, aliases = build_query(["a/b", "c/d", "e/f"])
        self.assertEqual(list(aliases.values()), ["a/b", "c/d", "e/f"])
        self.assertEqual(query.count("repository(owner:"), 3)
        self.assertIn("fragment facts on Repository", query)

    def test_a_missing_repository_is_absent_from_the_result(self):
        transport = FakeTransport(repos={"a/b": repository("a/b")})
        facts = source(transport).repository_facts(["a/b", "gone/away"])
        self.assertIn("a/b", facts)
        self.assertNotIn("gone/away", facts)
        self.assertEqual(len(transport.calls), 1)


class IdentityTest(unittest.TestCase):
    def test_package_name_comes_from_description_not_from_the_repository_name(self):
        node = repository("duckdb/duckdb-r", description_file="Package: duckdb\nVersion: 1.4.0\n")
        identity = identity_group(node)
        self.assertTrue(identity["is_r_package"])
        self.assertEqual(identity["package"], "duckdb")
        self.assertEqual(identity["version"], "1.4.0")

    def test_no_description_means_no_package_fields(self):
        identity = identity_group(repository("krlmlr/notapackage"))
        self.assertFalse(identity["is_r_package"])
        self.assertIsNone(identity["package"])
        self.assertIsNone(identity["version"])

    def test_archived_is_recorded(self):
        self.assertTrue(identity_group(repository("a/b", archived=True))["archived"])
        self.assertFalse(identity_group(repository("a/b"))["archived"])

    def test_links_are_fields(self):
        links = identity_group(repository("a/b", default_branch="trunk"))["links"]
        self.assertEqual(links["repository"], "https://github.com/a/b")
        self.assertIn("branch%3Atrunk", links["actions"])


class ReleaseTest(unittest.TestCase):
    def test_no_release_records_absent_rather_than_zero(self):
        group = release_group(repository("a/b", releases=[]), now=NOW)
        self.assertIsNone(group["latest_tag"])
        self.assertIsNone(group["commits_since"])
        self.assertIsNone(group["latest_age_days"])

    def test_commits_since_the_release_are_classified(self):
        node = repository(
            "a/b",
            releases=[{"tagName": "v1.0.0", "publishedAt": ago(30), "isDraft": False}],
            commits=[
                (ago(40), "feat: before the release"),
                (ago(20), "feat: after it"),
                (ago(10), "fix: also after"),
                (ago(5), "just a subject"),
            ],
        )
        group = release_group(node, now=NOW)
        self.assertEqual(group["commits_since"], 3)
        self.assertEqual(group["commits_by_type"], {"feat": 1, "fix": 1, "unclassified": 1})
        self.assertEqual(sum(group["commits_by_type"].values()), group["commits_since"])
        self.assertEqual(group["oldest_unreleased_at"], ago(20))

    def test_draft_release_is_three_states(self):
        with_draft = repository(
            "a/b",
            permission="WRITE",
            releases=[{"tagName": "v2", "createdAt": ago(1), "isDraft": True}, {"tagName": "v1", "publishedAt": ago(9), "isDraft": False}],
        )
        without_draft = repository("a/b", permission="WRITE", releases=[{"tagName": "v1", "publishedAt": ago(9), "isDraft": False}])
        no_push = repository("a/b", permission="READ", releases=[{"tagName": "v1", "publishedAt": ago(9), "isDraft": False}])
        self.assertEqual(release_group(with_draft, now=NOW)["draft_release"], "present")
        self.assertEqual(release_group(without_draft, now=NOW)["draft_release"], "none")
        self.assertEqual(release_group(no_push, now=NOW)["draft_release"], "unavailable")

    def test_a_draft_is_not_the_latest_release(self):
        node = repository(
            "a/b",
            permission="WRITE",
            releases=[{"tagName": "v2", "createdAt": ago(1), "isDraft": True}, {"tagName": "v1", "publishedAt": ago(9), "isDraft": False}],
        )
        self.assertEqual(release_group(node, now=NOW)["latest_tag"], "v1")


class ConventionalCommitsTest(unittest.TestCase):
    def test_buckets_sum_to_the_total(self):
        subjects = ["feat: a", "feat(scope): b", "fix!: c", "chore: d", "nope", "Merge pull request #1"]
        counts = classify_subjects(subjects)
        self.assertEqual(counts, {"chore": 1, "feat": 2, "fix": 1, "unclassified": 2})
        self.assertEqual(sum(counts.values()), len(subjects))


class CiTest(unittest.TestCase):
    def test_no_runs_is_absent_not_failing(self):
        group = ci_group([], window_days=90, now=NOW)
        self.assertIsNone(group["latest_conclusion"])
        self.assertEqual(group["consecutive_failures"], 0)
        self.assertIsNone(group["success_rate"])

    def test_three_failures_in_a_row(self):
        series = [
            run(conclusion="success", created=ago(20)),
            run(conclusion="failure", created=ago(9)),
            run(conclusion="failure", created=ago(5)),
            run(conclusion="failure", created=ago(1)),
        ]
        group = ci_group([run_entry(item) for item in series], window_days=90, now=NOW)
        self.assertEqual(group["consecutive_failures"], 3)
        self.assertEqual(group["red_since"], ago(9))
        self.assertEqual(group["success_rate"], 0.25)

    def test_alternating_and_green_is_not_consecutively_failing(self):
        series = [
            run(conclusion="failure", created=ago(20)),
            run(conclusion="success", created=ago(10)),
            run(conclusion="failure", created=ago(5)),
            run(conclusion="success", created=ago(1)),
        ]
        group = ci_group([run_entry(item) for item in series], window_days=90, now=NOW)
        self.assertEqual(group["consecutive_failures"], 0)
        self.assertIsNone(group["red_since"])
        self.assertEqual(group["success_rate"], 0.5)

    def test_the_window_actually_covered_is_recorded(self):
        series = [run_entry(run(conclusion="success", created=ago(7)))]
        group = ci_group(series, window_days=90, now=NOW)
        self.assertEqual(group["window_days"], 90)
        self.assertEqual(group["window_from"], ago(7))
        self.assertEqual(group["window_to"], ago(7))
        self.assertEqual(len(group["runs"]), 1)

    def test_runs_come_back_oldest_first(self):
        transport = FakeTransport(
            runs={"a/b": [run(conclusion="success", created=ago(1)), run(conclusion="failure", created=ago(30))]}
        )
        series = source(transport).workflow_runs("a/b", "main")
        self.assertEqual([item["created_at"] for item in series], [ago(30), ago(1)])
        self.assertEqual(series[0]["duration_seconds"], 600)


class TicketsTest(unittest.TestCase):
    def test_empty_tracker_is_zeros_with_no_ages(self):
        group = tickets_group(repository("a/b"), config=Config(), now=NOW)
        self.assertEqual(group["open_issues"], 0)
        self.assertEqual(group["open_pull_requests"], 0)
        self.assertIsNone(group["oldest_issue_age_days"])
        self.assertIsNone(group["oldest_pull_request_age_days"])

    def test_a_maintainer_reply_is_told_from_a_stranger_by_association(self):
        node = repository(
            "a/b",
            issues=[
                issue(created=ago(10), comments=["NONE", "CONTRIBUTOR"]),
                issue(created=ago(5), comments=["NONE", "MEMBER"]),
                issue(created=ago(3), comments=[]),
            ],
        )
        group = tickets_group(node, config=Config(), now=NOW)
        self.assertEqual(group["issues_no_maintainer_reply"], 2)
        self.assertEqual(group["oldest_issue_age_days"], 10)

    def test_a_thread_longer_than_we_fetched_is_not_called_unanswered(self):
        node = repository("a/b", issues=[issue(created=ago(10), comments=["NONE"] * 10, total=42)])
        self.assertEqual(tickets_group(node, config=Config(), now=NOW)["issues_no_maintainer_reply"], 0)

    def test_pull_request_cuts(self):
        node = repository(
            "a/b",
            pulls=[
                pull_request(created=ago(40), association="NONE"),
                pull_request(created=ago(30), bot=True),
                pull_request(created=ago(20), association="MEMBER", draft=True),
                pull_request(created=ago(2), association="MEMBER"),
                pull_request(created=ago(30), association="MEMBER", reviews=2),
            ],
        )
        group = tickets_group(node, config=Config(), now=NOW)
        self.assertEqual(group["pull_requests_bot"], 1)
        self.assertEqual(group["pull_requests_outside"], 1)
        self.assertEqual(group["pull_requests_draft"], 1)
        # The cuts overlap on purpose: a bot's pull request that nobody has looked at in a month
        # is waiting on us exactly as much as a stranger's is.
        self.assertEqual(group["pull_requests_awaiting_review"], 2)
        self.assertEqual(group["oldest_pull_request_age_days"], 40)


class ActivityTest(unittest.TestCase):
    def test_a_package_with_no_recent_commit_is_dormant(self):
        node = repository("a/b", last_commit=ago(500), commits_recent=0, authors=[])
        group = activity_group(node, config=Config(), now=NOW)
        self.assertTrue(group["dormant"])
        self.assertEqual(group["last_commit_age_days"], 500)

    def test_an_active_package_counts_commits_and_authors(self):
        node = repository("a/b", last_commit=ago(2), commits_recent=17, authors=["a", "b", "a"])
        group = activity_group(node, config=Config(), now=NOW)
        self.assertFalse(group["dormant"])
        self.assertEqual(group["commits_recent"], 17)
        self.assertEqual(group["authors_recent"], 2)


if __name__ == "__main__":
    unittest.main()
