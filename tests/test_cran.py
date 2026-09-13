"""CRAN, against pages recorded from the live service.

`check_results_tibble.html` and `check_results_here.html` were fetched during implementation: one
package with NOTEs and one that is clean. The deadline page is derived from that shape rather than
recorded, because no package with a live deadline was reachable when the fixtures were made.
"""

import unittest

from portfolio.cran import CranSource, parse_check_results
from portfolio.transport import Client

from tests.support import FakeTransport, check_page


def cran_source(**kwargs) -> tuple[CranSource, FakeTransport]:
    transport = FakeTransport(**kwargs)
    return CranSource(Client(transport=transport, sleep=lambda _: None)), transport


class ParseTest(unittest.TestCase):
    def test_a_package_with_a_note(self):
        parsed = parse_check_results(check_page("tibble"))
        self.assertEqual(parsed["worst_status"], "NOTE")
        self.assertEqual(parsed["status_counts"], {"NOTE": 5, "OK": 8})
        self.assertEqual(len(parsed["flavours"]), 13)
        self.assertIsNone(parsed["deadline"])

    def test_a_clean_package(self):
        parsed = parse_check_results(check_page("here"))
        self.assertEqual(parsed["worst_status"], "OK")
        self.assertEqual(parsed["status_counts"], {"OK": 13})

    def test_a_deadline_is_read_from_the_page(self):
        parsed = parse_check_results(check_page("RKazam"))
        self.assertEqual(parsed["deadline"], "2026-09-20")
        self.assertEqual(parsed["worst_status"], "ERROR")

    def test_an_unrecognised_page_yields_no_flavours(self):
        self.assertEqual(parse_check_results("<html><body>nothing here</body></html>")["flavours"], [])


class SourceTest(unittest.TestCase):
    def test_version_and_publication_date(self):
        source, _ = cran_source(
            cran={"tibble": (check_page("tibble"), "Package: tibble\nVersion: 3.3.1\nDate/Publication: 2026-01-11 09:20:02 UTC\n")}
        )
        group = source.package("tibble")
        self.assertEqual(group["state"], "available")
        self.assertEqual(group["version"], "3.3.1")
        self.assertEqual(group["published_at"], "2026-01-11")
        self.assertEqual(group["package_url"], "https://cran.r-project.org/package=tibble")

    def test_a_package_not_on_cran_is_absent_not_unavailable(self):
        source, _ = cran_source(cran={})
        self.assertEqual(source.package("neverpublished")["state"], "absent")

    def test_an_unreachable_service_is_unavailable(self):
        source, _ = cran_source(cran_down=True)
        group = source.package("tibble")
        self.assertEqual(group["state"], "unavailable")
        self.assertIsNone(group["worst_status"])

    def test_two_requests_per_package(self):
        source, transport = cran_source(
            cran={"tibble": (check_page("tibble"), "Package: tibble\nVersion: 3.3.1\nDate/Publication: 2026-01-11 09:20:02 UTC\n")}
        )
        source.package("tibble")
        self.assertEqual(len(transport.calls), 2)


if __name__ == "__main__":
    unittest.main()
