"""The optional online breach check, tested against a fake service (no network is used)."""
import re
import unittest
from unittest import mock

from tests.helpers import DataDirTest
from paksward import breach
from paksward.api import Api, Locked, PUBLIC

PW = "Zebra-4-Quartz-Lantern-91"
# SHA-1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8 (a well-known value)
PASSWORD_PREFIX, PASSWORD_SUFFIX = "5BAA6", "1E4C9B93F3F0682250B6CF8331B7EE68FD8"


class FakeService:
    """Answers like the real range API: every suffix under a prefix, plus padding lines with count 0."""
    def __init__(self, known):
        self.known, self.requests = {}, []
        for pw, count in known.items():
            prefix, suffix = breach.split_hash(pw)
            self.known.setdefault(prefix, {})[suffix] = count

    def __call__(self, prefix):
        self.requests.append(prefix)
        lines = [f"{s}:{c}" for s, c in self.known.get(prefix, {}).items()]
        lines += ["0" * 35 + ":0", "F" * 35 + ":0"]                      # padding
        return "\r\n".join(lines)


class TestBreachModule(unittest.TestCase):
    def test_hash_split_matches_the_known_value(self):
        self.assertEqual(breach.split_hash("password"), (PASSWORD_PREFIX, PASSWORD_SUFFIX))

    def test_parse_ignores_padding_and_junk(self):
        text = f"{PASSWORD_SUFFIX}:9545824\r\n{'A' * 35}:0\r\nnot a line\r\n{'B' * 34}:5\r\n"
        self.assertEqual(breach.parse_range(text), {PASSWORD_SUFFIX: 9545824})

    def test_only_five_character_prefixes_are_ever_sent_and_never_the_password(self):
        service = FakeService({"password": 100})
        counts, failed = breach.check(["password", "a-very-unlikely-password-91!"], fetch=service)
        self.assertEqual(counts, {"password": 100, "a-very-unlikely-password-91!": 0})
        self.assertEqual(failed, 0)
        for sent in service.requests:
            self.assertRegex(sent, r"^[0-9A-F]{5}$")
        self.assertNotIn("password", " ".join(service.requests).lower())

    def test_one_request_per_distinct_prefix_and_duplicates_are_merged(self):
        service = FakeService({})
        breach.check(["same", "same", "same"], fetch=service)
        self.assertEqual(len(service.requests), 1)

    def test_network_failures_are_counted_not_raised(self):
        def broken(prefix):
            raise breach.BreachCheckError("offline")
        self.assertEqual(breach.check(["a", "b"], fetch=broken), ({}, 2))

    def test_the_real_fetcher_refuses_anything_but_a_prefix(self):
        for bad in ("password", "5BAA61", "5baa6", "", "5BAA6/../x"):
            with self.assertRaises(ValueError):
                breach.fetch_range(bad)

    def test_the_real_fetcher_asks_only_for_the_prefix_over_https(self):
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def geturl(self): return breach.URL + PASSWORD_PREFIX
            def read(self, n): return b"A" * 35 + b":0\r\n"
        with mock.patch("urllib.request.urlopen", return_value=Resp()) as opened:
            breach.fetch_range(PASSWORD_PREFIX)
        request = opened.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.pwnedpasswords.com/range/5BAA6")
        self.assertEqual(request.get_header("Add-padding"), "true")
        self.assertIsNone(request.data)                                  # a plain GET with no body
        self.assertNotIn("@", request.get_header("User-agent"))          # no personal details in the client name

    def test_a_redirect_away_from_the_service_is_refused(self):
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def geturl(self): return "https://evil.example/" + PASSWORD_PREFIX
            def read(self, n): return b""
        with mock.patch("urllib.request.urlopen", return_value=Resp()):
            with self.assertRaises(breach.BreachCheckError):
                breach.fetch_range(PASSWORD_PREFIX)


class TestBreachApi(DataDirTest):
    def setUp(self):
        super().setUp()
        self.service = FakeService({"Summer2019!": 4321, "password": 99})
        self.api = Api(breach_fetch=self.service, copy_fn=lambda t, s: True)
        self.assertTrue(self.api.register("a@b.co", PW, PW)["ok"])

    def add(self, site, pw):
        return self.api.add_entry({"website": site, "username": "u", "password": pw})["id"]

    def test_is_public_and_needs_an_unlocked_vault(self):
        self.assertIn("check_breaches", PUBLIC)
        self.api.lock()
        with self.assertRaises(Locked):
            self.api.check_breaches()

    def test_reports_which_entries_are_compromised_with_counts(self):
        leaked, fine = self.add("x.com", "Summer2019!"), self.add("y.com", "Qm7#vT2!zLp9Xr4K")
        r = self.api.check_breaches()
        self.assertTrue(r["ok"])
        self.assertEqual((r["checked"], r["failed"]), (2, 0))
        self.assertEqual(r["compromised"], {leaked: 4321})
        self.assertNotIn(fine, r["compromised"])

    def test_nothing_is_sent_for_an_empty_vault(self):
        r = self.api.check_breaches()
        self.assertEqual((r["ok"], r["compromised"], self.service.requests), (True, {}, []))

    def test_offline_gives_a_clear_error_and_changes_nothing(self):
        self.add("x.com", "Summer2019!")
        def offline(prefix):
            raise breach.BreachCheckError("offline")
        self.api._breach_fetch = offline
        r = self.api.check_breaches()
        self.assertFalse(r["ok"])
        self.assertIn("internet", r["error"])
        self.assertEqual(len(self.api.list_entries()), 1)

    def test_the_vault_never_sends_more_than_prefixes(self):
        self.add("x.com", "Summer2019!")
        self.api.check_breaches()
        self.assertTrue(all(re.fullmatch(r"[0-9A-F]{5}", p) for p in self.service.requests))


if __name__ == "__main__":
    unittest.main()
