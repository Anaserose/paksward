"""Strength, generator, entry model and Watchtower report."""
import string
import unittest
from datetime import datetime, timedelta, timezone

from tests.helpers import ROOT  # noqa: F401  (puts the project on sys.path)
from paksward import entries as E, generator, strength, watchtower
from paksward.wordlist import WORDS


class TestStrength(unittest.TestCase):
    def label(self, pw):
        return strength.check_strength(pw)["label"]

    def test_empty_is_terrible(self):
        self.assertEqual(strength.check_strength(""), {"bits": 0, "level": 0, "label": "Terrible"})

    def test_known_bad_passwords(self):
        for pw in ("password123", "12345678", "qwerty", "aaaaaaaa", "letmein"):
            self.assertEqual(strength.check_strength(pw)["level"], 0, pw)

    def test_dictionary_word_plus_year_is_not_strong(self):
        self.assertLessEqual(strength.check_strength("Summer2019!")["level"], 1)
        self.assertLessEqual(strength.check_strength("Hunter2024")["level"], 1)

    def test_long_random_is_excellent(self):
        self.assertEqual(self.label("Xc9@bN4#vLt6Hm2P"), "Excellent")

    def test_longer_is_never_weaker_for_random_text(self):
        a = strength.check_strength("Kq7#mZ")["bits"]
        b = strength.check_strength("Kq7#mZx2Rt9!")["bits"]
        self.assertGreater(b, a)

    def test_unicode_does_not_crash(self):
        self.assertIn(strength.check_strength("pässwörd ✓ ünï")["level"], range(5))

    def test_famous_passphrases_and_tricks_are_not_rated_highly(self):
        for pw in ("Zebra-4-Quartz-Lantern-91", "correct horse battery staple", "Tr0ub4dor&3", "P@ssw0rd!", "Lagos2024!",
                   "p\u00e4ssw\u00f6rd", "Password1234", "iloveyou2020"):
            self.assertLessEqual(strength.check_strength(pw)["level"], 2, pw)

    def test_the_old_overrating_is_gone(self):
        self.assertLess(strength.check_strength("Zebra-4-Quartz-Lantern-91")["bits"], 50)

    def test_what_the_generator_makes_is_rated_strong(self):
        levels = [strength.check_strength(generator.generate({"length": 16})["password"])["level"] for _ in range(300)]
        self.assertGreaterEqual(min(levels), 2)                        # a chance pattern may cost a level, never more
        self.assertGreaterEqual(sum(l >= 3 for l in levels), 285)      # and almost all are Strong or better

    def test_generated_passphrases_are_not_overrated_against_the_generators_own_bits(self):
        for _ in range(30):
            g = generator.generate({"mode": "passphrase", "words": 5})
            self.assertLessEqual(strength.check_strength(g["password"])["bits"], g["bits"] + 8)

    def test_very_long_input_is_fast(self):
        import time
        start = time.perf_counter()
        strength.check_strength("Ab3$" * 256)
        self.assertLess(time.perf_counter() - start, 1.0)

    def test_levels_cover_thresholds(self):
        self.assertEqual([strength.level_for(b) for b in (0, 25.9, 26, 39.9, 40, 59.9, 60, 79.9, 80, 200)],
                         [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])


class TestGeneratorV3(unittest.TestCase):
    def test_default_has_every_class_and_length(self):
        for _ in range(100):
            r = generator.generate({"length": 20})
            pw = r["password"]
            self.assertEqual(len(pw), 20)
            self.assertTrue(any(c in string.ascii_lowercase for c in pw))
            self.assertTrue(any(c in string.ascii_uppercase for c in pw))
            self.assertTrue(any(c in string.digits for c in pw))
            self.assertTrue(any(c in "!@#$%^&*()-_=+?" for c in pw))

    def test_options_respected(self):
        for _ in range(100):
            pw = generator.generate({"length": 16, "upper": False, "symbols": False, "digits": False})["password"]
            self.assertTrue(pw.islower() and pw.isalpha())

    def test_all_classes_off_falls_back_to_lowercase(self):
        pw = generator.generate({"lower": False, "upper": False, "digits": False, "symbols": False})["password"]
        self.assertTrue(pw.islower())

    def test_avoid_ambiguous(self):
        for _ in range(200):
            pw = generator.generate({"length": 40, "avoidAmbiguous": True})["password"]
            self.assertFalse(set(pw) & set("Il1O0o"), pw)

    def test_length_is_clamped(self):
        self.assertEqual(len(generator.generate({"length": 2})["password"]), 8)
        self.assertEqual(len(generator.generate({"length": 999})["password"]), 64)
        self.assertEqual(len(generator.generate({"length": None})["password"]), 16)
        self.assertEqual(len(generator.generate({})["password"]), 16)

    def test_passphrase(self):
        r = generator.generate({"mode": "passphrase", "words": 6, "separator": "-", "capitalize": True, "digits": True})
        parts = r["password"].split("-")
        self.assertEqual(len(parts), 7)                       # 6 words + a number
        self.assertTrue(all(p[0].isupper() for p in parts[:6]))
        self.assertTrue(parts[6].isdigit())
        self.assertTrue(all(p.lower() in WORDS for p in parts[:6]))

    def test_passphrase_bits_come_from_the_real_list_size(self):
        import math
        r = generator.generate({"mode": "passphrase", "words": 5})
        self.assertEqual(r["bits"], round(5 * math.log2(len(WORDS))))

    def test_wordlist_has_no_duplicates_or_blanks(self):
        self.assertEqual(len(WORDS), len(set(WORDS)))
        self.assertTrue(all(w.isalpha() and w.islower() for w in WORDS))

    def test_outputs_are_not_repeated(self):
        self.assertEqual(len({generator.generate({"length": 24})["password"] for _ in range(50)}), 50)


class TestEntries(unittest.TestCase):
    def test_normalize_fills_entries_saved_without_newer_fields(self):
        es = [{"website": "a", "username": "u", "password": "p"}, {"website": "b", "username": "u", "password": "q"}]
        self.assertTrue(E.normalize(es))
        self.assertEqual(len({e["id"] for e in es}), 2)
        self.assertTrue(all(e["category"] == "Other" and e["favorite"] is False for e in es))
        self.assertTrue(all("updated_at" not in e for e in es))       # unknown stays unknown
        self.assertFalse(E.normalize(es))                             # second pass changes nothing

    def test_duplicate_ids_are_repaired(self):
        es = [{"id": "x", "website": "a", "username": "u", "password": "p", "category": "Work", "favorite": False},
              {"id": "x", "website": "b", "username": "u", "password": "q", "category": "Work", "favorite": False}]
        E.normalize(es)
        self.assertNotEqual(es[0]["id"], es[1]["id"])

    def test_unknown_category_becomes_other(self):
        es = [{"website": "a", "username": "u", "password": "p", "category": "Hacking"}]
        E.normalize(es)
        self.assertEqual(es[0]["category"], "Other")

    def test_age_days(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        self.assertAlmostEqual(E.age_days({"updated_at": (now - timedelta(days=10)).isoformat()}, now), 10, places=3)
        self.assertIsNone(E.age_days({}, now))
        self.assertIsNone(E.age_days({"updated_at": "not a date"}, now))
        self.assertEqual(E.age_days({"updated_at": (now + timedelta(days=5)).isoformat()}, now), 0)


def mk(i, pw, days=None, now=None):
    e = {"id": i, "website": f"{i}.com", "username": "u", "password": pw, "category": "Other", "favorite": False}
    if days is not None:
        e["updated_at"] = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
    return e


class TestWatchtower(unittest.TestCase):
    def test_reuse_groups(self):
        es = [mk("a", "same"), mk("b", "same"), mk("c", "other"), mk("d", "third"), mk("e", "third"), mk("f", "third")]
        groups = sorted(sorted(g) for g in watchtower.reuse_groups(es))
        self.assertEqual(groups, [["a", "b"], ["d", "e", "f"]])
        self.assertEqual(watchtower.reuse_counts(es)["d"], 3)
        self.assertNotIn("c", watchtower.reuse_counts(es))

    def test_reuse_is_case_sensitive(self):
        self.assertEqual(watchtower.reuse_groups([mk("a", "Pass"), mk("b", "pass")]), [])

    def test_meta_never_contains_the_password(self):
        m = watchtower.entry_meta(mk("a", "TOPSECRET-value-1"))
        self.assertNotIn("password", m)
        self.assertNotIn("TOPSECRET", repr(m))

    def test_report_counts(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        es = [mk("a", "Xc9@bN4#vLt6Hm2P", 10, now), mk("b", "password123", 400, now), mk("c", "Summer2019!", 400, now),
              mk("d", "Summer2019!", 5, now), mk("e", "Kq7#mZx2Rt9!pL4w", None)]
        r = watchtower.security_report(es, now)
        self.assertEqual(r["total"], 5)
        self.assertEqual(sorted(r["weak"]), ["b", "c", "d"])
        self.assertEqual(sorted(r["old"]), ["b", "c"])               # "e" has no date: unknown, not old
        self.assertEqual(sorted(sorted(g) for g in r["reused"]), [["c", "d"]])
        self.assertEqual(sum(r["levels"]), 5)
        self.assertTrue(0 <= r["score"] <= 100)

    def test_empty_vault_scores_100(self):
        r = watchtower.security_report([])
        self.assertEqual((r["score"], r["total"], r["levels"]), (100, 0, [0] * 5))

    def test_all_strong_unique_recent_scores_100(self):
        es = [mk("a", "Xc9@bN4#vLt6Hm2P", 1), mk("b", "Kq7#mZx2Rt9!pL4w", 1)]
        self.assertEqual(watchtower.security_report(es)["score"], 100)

    def test_fair_passwords_are_not_a_perfect_score(self):
        fair = "tiger-orange-cloud-7"
        self.assertEqual(strength.check_strength(fair)["label"], "Fair")
        r = watchtower.security_report([mk("a", fair, 1), mk("b", "Xc9@bN4#vLt6Hm2P", 1)])
        self.assertLess(r["score"], 100)
        self.assertEqual(r["weak"], [])                              # still not flagged as weak

    def test_score_drops_when_problems_added(self):
        good = [mk("a", "Xc9@bN4#vLt6Hm2P", 1)]
        worse = good + [mk("b", "password123", 1), mk("c", "password123", 1)]
        self.assertLess(watchtower.security_report(worse)["score"], watchtower.security_report(good)["score"])


if __name__ == "__main__":
    unittest.main()
