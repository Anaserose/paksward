"""The session layer the interface talks to, run against a real (temporary) vault on disk."""
import json
import os
import shutil
import time
import unittest
from unittest import mock

from tests.helpers import Clock, DataDirTest, read_text
from paksward import clipboard, config, storage
from paksward.api import Api, Locked, PUBLIC

PW = "Zebra-4-Quartz-Lantern-91"


def new_api(clock=None, copy_fn=None):
    return Api(clock=clock or Clock(), copy_fn=copy_fn or (lambda t, s: True))


def sign_up(api, email="Alice@Example.com"):
    r = api.register(email, PW, PW)
    assert r["ok"], r
    return r


class TestAccountFlows(DataDirTest):
    def test_register_login_lock(self):
        api = new_api()
        sign_up(api)
        self.assertTrue(api.status()["unlocked"])
        api.lock()
        self.assertFalse(api.status()["unlocked"])
        with self.assertRaises(Locked):
            api.list_entries()
        self.assertTrue(api.login("alice@example.com", PW)["ok"])
        self.assertEqual(api.list_entries(), [])

    def test_register_validation(self):
        api = new_api()
        bad = [api.register("", PW, PW), api.register("nope", PW, PW),
               api.register("a@b.co", "short", "short"), api.register("a@b.co", PW, "diff"),
               api.register("a@b.co", "password123", "password123")]          # long enough but easy to guess
        self.assertTrue(all(not r["ok"] and r["error"] for r in bad))
        self.assertEqual(storage.load_users(), {})                     # nothing was created

    def test_registration_returns_both_keys_once(self):
        r = sign_up(new_api())
        self.assertTrue(r["kit"]["secret_key"].startswith("PWSK-"))
        self.assertTrue(r["kit"]["recovery_key"].startswith("PWRK-"))
        self.assertNotIn("kit", new_api().login("alice@example.com", PW))

    def test_duplicate_email_rejected_case_insensitively(self):
        sign_up(new_api())
        r = new_api().register("ALICE@example.com", PW, PW)
        self.assertFalse(r["ok"])

    def test_wrong_password_counts_down_then_locks(self):
        api = new_api()
        sign_up(api)
        api.lock()
        msgs = [api.login("alice@example.com", "wrong-pass")["error"] for _ in range(5)]
        self.assertIn("4 attempt(s) left", msgs[0])
        self.assertIn("1 attempt(s) left", msgs[3])
        self.assertIn("locked for 24 hours", msgs[4])
        r = api.login("alice@example.com", PW)                         # even the right password is refused now
        self.assertFalse(r["ok"])
        self.assertIn("Try again in", r["error"])

    def test_successful_login_resets_failures(self):
        api = new_api()
        sign_up(api)
        api.lock()
        for _ in range(3):
            api.login("alice@example.com", "wrong-pass")
        self.assertTrue(api.login("alice@example.com", PW)["ok"])
        self.assertEqual(storage.load_users()["alice@example.com"]["failed_attempts"], 0)

    def test_unknown_email_and_bad_input(self):
        api = new_api()
        self.assertIn("No account", api.login("ghost@x.com", "whatever1")["error"])
        self.assertIn("valid email", api.login("not-an-email", "whatever1")["error"])
        self.assertIn("both", api.login("", "")["error"])

    def test_recovery_resets_password_and_keeps_vault(self):
        api = new_api()
        recovery = sign_up(api)["kit"]["recovery_key"]
        api.add_entry({"website": "github.com", "username": "alice", "password": "gh-Pass#1"})
        api.lock()
        self.assertTrue(api.recover_start("alice@example.com")["ok"])
        self.assertFalse(api.recover_verify("PWRK-AAAA-AAAA")["ok"])
        self.assertTrue(api.recover_verify(recovery.lower().replace("-", " "))["ok"])
        self.assertFalse(api.recover_reset("short", "short")["ok"])
        r = api.recover_reset("brand-new-pw-1", "brand-new-pw-1")
        self.assertTrue(r["ok"])
        self.assertIn("secret_key", r["kit"])                          # the Secret Key is reissued
        self.assertEqual(len(api.list_entries()), 1)
        api.lock()
        self.assertFalse(api.login("alice@example.com", PW)["ok"])
        self.assertTrue(api.login("alice@example.com", "brand-new-pw-1")["ok"])

    def test_a_new_device_needs_the_secret_key(self):
        api = new_api()
        secret = sign_up(api)["kit"]["secret_key"]
        api.lock()
        shutil.rmtree(config.SECRET_DIR)                               # as if the data folder was copied elsewhere
        r = api.login("alice@example.com", PW)
        self.assertFalse(r["ok"])
        self.assertTrue(r["need_secret"])
        self.assertEqual(storage.load_users()["alice@example.com"].get("failed_attempts", 0), 0)
        r = api.login("alice@example.com", PW, "PWSK-AAAA-AAAA")        # malformed key
        self.assertFalse(r["ok"])
        self.assertTrue(api.login("alice@example.com", PW, secret)["ok"])
        api.lock()
        self.assertTrue(api.login("alice@example.com", PW)["ok"])      # remembered on this device now

    def test_data_folder_alone_cannot_be_opened_even_with_the_right_password(self):
        api = new_api()
        sign_up(api)
        api.lock()
        shutil.rmtree(config.SECRET_DIR)
        self.assertFalse(api.login("alice@example.com", PW)["ok"])
        self.assertFalse(api.login("alice@example.com", PW, "PWSK-" + "AAAA-" * 8 + "AAAA")["ok"])

    def test_change_password_and_new_recovery_key(self):
        api = new_api()
        old_recovery = sign_up(api)["kit"]["recovery_key"]
        self.assertFalse(api.change_password("wrong", "another-pw-77x", "another-pw-77x")["ok"])
        self.assertTrue(api.change_password(PW, "another-pw-77x", "another-pw-77x")["ok"])
        new_recovery = api.new_recovery_key()["recovery_key"]
        api.lock()
        self.assertFalse(api.login("alice@example.com", PW)["ok"])
        self.assertTrue(api.login("alice@example.com", "another-pw-77x")["ok"])
        api.lock()
        api.recover_start("alice@example.com")
        self.assertFalse(api.recover_verify(old_recovery)["ok"])
        self.assertTrue(api.recover_verify(new_recovery)["ok"])

    def test_secret_key_can_be_shown_while_signed_in(self):
        api = new_api()
        secret = sign_up(api)["kit"]["secret_key"]
        self.assertEqual(api.get_secret_key()["secret_key"], secret)
        api.lock()
        with self.assertRaises(Locked):
            api.get_secret_key()

    def test_cannot_skip_recovery_steps(self):
        api = new_api()
        sign_up(api)
        api.lock()
        self.assertFalse(api.recover_reset("brand-new-pw-1", "brand-new-pw-1")["ok"])
        api.recover_start("alice@example.com")
        self.assertFalse(api.recover_reset("brand-new-pw-1", "brand-new-pw-1")["ok"])     # not verified yet
        self.assertFalse(api.status()["unlocked"])

    def test_recovery_attempts_lock_the_account(self):
        api = new_api()
        sign_up(api)
        api.lock()
        api.recover_start("alice@example.com")
        results = [api.recover_verify("PWRK-AAAA-AAAA") for _ in range(5)]
        self.assertIn("Locked for 24 hours", results[-1]["error"])
        self.assertFalse(api.recover_start("alice@example.com")["ok"])

    def test_corrupt_users_file_is_not_overwritten(self):
        with open(config.USERS_FILE, "w") as f:
            f.write("{bad json")
        with self.assertRaises(ValueError):
            Api()
        self.assertEqual(read_text(config.USERS_FILE), "{bad json")


class TestEntries(DataDirTest):
    def setUp(self):
        super().setUp()
        self.api = new_api()
        sign_up(self.api)

    def add(self, site="github.com", pw="gh-Pass#1", **kw):
        r = self.api.add_entry({"website": site, "username": "alice", "password": pw, **kw})
        self.assertTrue(r["ok"], r)
        return r["id"]

    def test_list_never_contains_passwords(self):
        self.add(pw="SECRET-VALUE-123")
        listing = self.api.list_entries()
        self.assertNotIn("SECRET-VALUE-123", json.dumps(listing))
        self.assertNotIn("password", listing[0])
        self.assertNotIn("SECRET-VALUE-123", json.dumps(self.api.security_report()))

    def test_get_entry_returns_password(self):
        i = self.add(pw="SECRET-VALUE-123")
        self.assertEqual(self.api.get_entry(i)["entry"]["password"], "SECRET-VALUE-123")
        self.assertFalse(self.api.get_entry("nope")["ok"])

    def test_everything_survives_restart(self):
        i = self.add(category="Banking", favorite=True)
        self.api.lock()
        again = new_api()
        again.login("alice@example.com", PW)
        e = again.get_entry(i)["entry"]
        self.assertEqual((e["website"], e["category"], e["favorite"]), ("github.com", "Banking", True))

    def test_updated_at_changes_only_with_the_password(self):
        i = self.add()
        e = self.api.entries[0]
        e["updated_at"] = "2020-01-01T00:00:00+00:00"
        self.api.update_entry(i, {"website": "github.com", "username": "alice2", "password": "gh-Pass#1", "category": "Work"})
        self.assertEqual(e["updated_at"], "2020-01-01T00:00:00+00:00")
        self.api.update_entry(i, {"website": "github.com", "username": "alice2", "password": "new-pass-9", "category": "Work"})
        self.assertNotEqual(e["updated_at"], "2020-01-01T00:00:00+00:00")
        self.assertEqual(e["username"], "alice2")

    def test_validation(self):
        self.assertFalse(self.api.add_entry({"website": "", "username": "u", "password": "p"})["ok"])
        self.assertFalse(self.api.add_entry({"website": "w", "username": "u"})["ok"])
        self.assertFalse(self.api.add_entry(None)["ok"])
        i = self.add()
        self.assertFalse(self.api.update_entry(i, {"website": "w", "username": "", "password": "p"})["ok"])
        self.assertEqual(self.api.add_entry({"website": "w", "username": "u", "password": "p", "category": "Nope"})["ok"], True)
        self.assertEqual(self.api.entries[-1]["category"], "Other")

    def test_favorite_and_delete(self):
        i = self.add()
        self.api.set_favorite(i, True)
        self.assertTrue(self.api.list_entries()[0]["favorite"])
        self.assertTrue(self.api.delete_entry(i)["ok"])
        self.assertEqual(self.api.list_entries(), [])
        self.assertFalse(self.api.delete_entry(i)["ok"])

    def test_failed_disk_write_leaves_memory_and_disk_consistent(self):
        i = self.add()
        with mock.patch.object(storage, "save_vault", side_effect=OSError("disk full")):
            self.assertFalse(self.api.add_entry({"website": "x.com", "username": "u", "password": "p"})["ok"])
            self.assertFalse(self.api.update_entry(i, {"website": "g", "username": "u", "password": "zzz"})["ok"])
            self.assertFalse(self.api.delete_entry(i)["ok"])
            self.assertFalse(self.api.set_favorite(i, True)["ok"])
        self.assertEqual(len(self.api.entries), 1)
        self.assertEqual(self.api.entries[0]["password"], "gh-Pass#1")
        self.assertFalse(self.api.entries[0]["favorite"])

    def test_vault_file_is_encrypted_on_disk(self):
        self.add(pw="SECRET-VALUE-123")
        for name in os.listdir(config.VAULTS_DIR):
            with open(os.path.join(config.VAULTS_DIR, name), "rb") as f:
                raw = f.read()
            self.assertGreater(len(raw), 50)
            self.assertNotIn(b"SECRET-VALUE-123", raw)
            self.assertNotIn(b"github.com", raw)

    def test_report_reflects_vault(self):
        self.add("a.com", "password123")
        self.add("b.com", "password123")
        r = self.api.security_report()
        self.assertEqual(len(r["reused"]), 1)
        self.assertEqual(len(r["weak"]), 2)


class TestAutoLock(DataDirTest):
    def setUp(self):
        super().setUp()
        self.clock = Clock()
        self.api = new_api(self.clock)
        sign_up(self.api)
        self.api.add_entry({"website": "a.com", "username": "u", "password": "p-ass-w0rd-X9"})

    def test_default_is_five_minutes(self):
        self.assertEqual(self.api.get_settings()["settings"]["autolock_minutes"], 5)
        self.clock.advance(299)
        self.api.list_entries()
        self.clock.advance(301)
        with self.assertRaises(Locked):
            self.api.list_entries()

    def test_lock_wipes_session_state(self):
        self.api.set_settings({"autolock_minutes": 2})
        self.clock.advance(121)
        with self.assertRaises(Locked):
            self.api.list_entries()
        self.assertEqual((self.api.entries, self.api.vault_key, self.api.fernet, self.api.email), ([], None, None, None))
        self.assertFalse(self.api.status()["unlocked"])

    def test_activity_extends_the_timer(self):
        self.api.set_settings({"autolock_minutes": 2})
        for _ in range(5):
            self.clock.advance(100)
            self.api.touch()
        self.assertTrue(self.api.status()["unlocked"])

    def test_off_never_locks(self):
        self.api.set_settings({"autolock_minutes": 0})
        self.clock.advance(10 * 24 * 3600)
        self.assertEqual(len(self.api.list_entries()), 1)

    def test_setting_persists_and_is_validated(self):
        self.assertFalse(self.api.set_settings({"autolock_minutes": 7})["ok"])
        self.api.set_settings({"autolock_minutes": 10})
        self.assertEqual(storage.load_users()["alice@example.com"]["autolock_minutes"], 10)
        self.api.lock()
        again = new_api(self.clock)
        again.login("alice@example.com", PW)
        self.assertEqual(again.get_settings()["settings"]["autolock_minutes"], 10)

    def test_idle_lock_requires_the_password_again(self):
        self.clock.advance(10_000)
        with self.assertRaises(Locked):
            self.api.get_entry("x")
        self.assertFalse(self.api.login("alice@example.com", "wrong-pass")["ok"])
        self.assertTrue(self.api.login("alice@example.com", PW)["ok"])


class TestClipboardTimer(unittest.TestCase):
    def test_clears_only_if_unchanged(self):
        box = {"v": None}
        cp = lambda t: box.update(v=t) or True
        ps = lambda: box["v"]
        self.assertTrue(clipboard.copy_and_schedule_clear("secret", 0.05, cp, ps))
        self.assertEqual(box["v"], "secret")
        time.sleep(0.2)
        self.assertEqual(box["v"], "")

    def test_leaves_clipboard_alone_if_user_copied_something_else(self):
        box = {"v": None}
        cp = lambda t: box.update(v=t) or True
        ps = lambda: box["v"]
        clipboard.copy_and_schedule_clear("secret", 0.1, cp, ps)
        box["v"] = "something the user copied later"
        time.sleep(0.25)
        self.assertEqual(box["v"], "something the user copied later")

    def test_reports_failure_when_no_clipboard(self):
        self.assertFalse(clipboard.copy_and_schedule_clear("x", 1, lambda t: False, lambda: None))

    def test_new_copy_cancels_older_timer(self):
        box = {"v": None}
        cp = lambda t: box.update(v=t) or True
        ps = lambda: box["v"]
        clipboard.copy_and_schedule_clear("first", 0.1, cp, ps)
        clipboard.copy_and_schedule_clear("second", 0.4, cp, ps)
        time.sleep(0.25)
        self.assertEqual(box["v"], "second")
        time.sleep(0.4)
        self.assertEqual(box["v"], "")


class TestApiSurface(unittest.TestCase):
    def test_public_methods_exist_and_are_not_private(self):
        for name in PUBLIC:
            self.assertFalse(name.startswith("_"))
            self.assertTrue(callable(getattr(Api, name)), name)

    def test_internal_methods_are_not_exposed(self):
        for name in ("_enter", "_persist", "_require", "users", "vault_key", "entries", "fernet", "__init__"):
            self.assertNotIn(name, PUBLIC)


if __name__ == "__main__":
    unittest.main()
