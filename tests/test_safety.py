"""Vault-loss protection, recovery sessions, the slow breach check, and settings that fail to save."""
import os
import threading
import unittest
from unittest import mock

from tests.helpers import Clock, DataDirTest, read_bytes, write_text
from paksward import accounts, breach, storage
from paksward.api import Api, Locked, RECOVERY_SECONDS

PW = "Zebra-4-Quartz-Lantern-91"


def signed_up(api, email="a@b.co"):
    r = api.register(email, PW, PW)
    assert r["ok"], r
    return r["kit"]["recovery_key"]


class TestVaultIsNeverSilentlyReplaced(DataDirTest):
    def make(self):
        api = Api(copy_fn=lambda t, s: True)
        signed_up(api)
        api.add_entry({"website": "x.com", "username": "u", "password": "Qm7#vT2!zLp9Xr4K"})
        api.lock()
        return api, storage.vault_path_for("a@b.co")

    def test_a_missing_vault_is_refused_and_not_recreated(self):
        api, path = self.make()
        os.remove(path)
        r = api.login("a@b.co", PW)
        self.assertFalse(r["ok"])
        self.assertIn("missing", r["error"])
        self.assertFalse(os.path.exists(path))
        self.assertFalse(api.status()["unlocked"])

    def test_an_empty_vault_file_is_refused_and_left_alone(self):
        api, path = self.make()
        with open(path, "wb"):
            pass
        r = api.login("a@b.co", PW)
        self.assertFalse(r["ok"])
        self.assertIn("empty", r["error"])
        self.assertEqual(read_bytes(path), b"")

    def test_damaged_ciphertext_is_refused_and_left_alone(self):
        api, path = self.make()
        data = bytearray(read_bytes(path))
        data[len(data) // 2] ^= 0x01
        storage.atomic_write(path, bytes(data))
        before = read_bytes(path)
        r = api.login("a@b.co", PW)
        self.assertFalse(r["ok"])
        self.assertIn("corrupted", r["error"])
        self.assertEqual(read_bytes(path), before)

    def test_a_vault_encrypted_with_another_key_is_refused(self):
        api, path = self.make()
        from cryptography.fernet import Fernet
        other = Fernet(Fernet.generate_key()).encrypt(b"[]")
        storage.atomic_write(path, other)
        self.assertFalse(api.login("a@b.co", PW)["ok"])
        self.assertEqual(read_bytes(path), other)

    def test_nothing_can_be_saved_after_a_refused_login(self):
        api, path = self.make()
        os.remove(path)
        api.login("a@b.co", PW)
        with self.assertRaises(Locked):
            api.add_entry({"website": "new.com", "username": "u", "password": "pw-1234567890!"})
        self.assertFalse(os.path.exists(path))

    def test_new_accounts_still_work_and_start_with_a_real_empty_vault(self):
        api = Api(copy_fn=lambda t, s: True)
        signed_up(api, "fresh@b.co")
        self.assertTrue(os.path.getsize(storage.vault_path_for("fresh@b.co")) > 0)
        self.assertEqual(api.list_entries(), [])
        api.lock()
        self.assertTrue(api.login("fresh@b.co", PW)["ok"])

    def test_a_restored_copy_works_again(self):
        api, path = self.make()
        good = read_bytes(path)
        os.remove(path)
        self.assertFalse(api.login("a@b.co", PW)["ok"])
        storage.atomic_write(path, good)                           # restored from a backup
        self.assertTrue(api.login("a@b.co", PW)["ok"])
        self.assertEqual(len(api.list_entries()), 1)


class TestRecoverySessions(DataDirTest):
    def setUp(self):
        super().setUp()
        self.clock = Clock()
        self.api = Api(clock=self.clock, copy_fn=lambda t, s: True)
        self.recovery = signed_up(self.api)
        self.api.lock()

    def test_a_verified_recovery_expires_and_forgets_the_key(self):
        self.api.recover_start("a@b.co")
        self.assertTrue(self.api.recover_verify(self.recovery)["ok"])
        self.clock.advance(RECOVERY_SECONDS + 1)
        r = self.api.recover_reset("Brand-New-Pass-44-xq", "Brand-New-Pass-44-xq")
        self.assertFalse(r["ok"])
        self.assertIsNone(self.api._recovery)
        self.assertTrue(self.api.login("a@b.co", PW)["ok"])        # the old password still works

    def test_an_unstarted_or_stale_start_cannot_be_verified(self):
        self.api.recover_start("a@b.co")
        self.clock.advance(RECOVERY_SECONDS + 1)
        self.assertFalse(self.api.recover_verify(self.recovery)["ok"])

    def test_recovery_within_the_time_limit_still_works(self):
        self.api.recover_start("a@b.co")
        self.clock.advance(RECOVERY_SECONDS - 5)
        self.assertTrue(self.api.recover_verify(self.recovery)["ok"])
        self.assertTrue(self.api.recover_reset("Brand-New-Pass-44-xq", "Brand-New-Pass-44-xq")["ok"])

    def test_an_account_locked_during_recovery_cannot_continue(self):
        self.api.recover_start("a@b.co")
        for _ in range(5):
            self.api.login("a@b.co", "wrong password")
        self.assertFalse(self.api.recover_verify(self.recovery)["ok"])         # even with the right key
        self.assertFalse(self.api.recover_reset("Brand-New-Pass-44-xq", "Brand-New-Pass-44-xq")["ok"])

    def test_a_verified_recovery_is_dropped_if_the_account_becomes_locked(self):
        self.api.recover_start("a@b.co")
        self.assertTrue(self.api.recover_verify(self.recovery)["ok"])
        for _ in range(5):
            self.api.login("a@b.co", "wrong password")
        self.assertFalse(self.api.recover_reset("Brand-New-Pass-44-xq", "Brand-New-Pass-44-xq")["ok"])
        self.assertIsNone(self.api._recovery)

    def test_locking_cancels_a_recovery_in_progress(self):
        self.api.recover_start("a@b.co")
        self.api.recover_verify(self.recovery)
        self.api.lock()
        self.assertFalse(self.api.recover_reset("Brand-New-Pass-44-xq", "Brand-New-Pass-44-xq")["ok"])


class TestSlowBreachCheck(DataDirTest):
    def test_locking_works_while_a_check_is_waiting_on_the_network(self):
        started, release = threading.Event(), threading.Event()

        def slow_fetch(prefix):
            started.set()
            release.wait(10)
            return ""

        api = Api(breach_fetch=slow_fetch, copy_fn=lambda t, s: True)
        signed_up(api)
        api.add_entry({"website": "x.com", "username": "u", "password": "Qm7#vT2!zLp9Xr4K"})
        outcome = {}

        def run():
            try:
                outcome["result"] = api.check_breaches()
            except Locked:
                outcome["locked"] = True

        t = threading.Thread(target=run)
        t.start()
        self.assertTrue(started.wait(5))
        self.assertTrue(api.mutex.acquire(timeout=1), "the shared lock must be free during the network wait")
        try:
            api.lock()                                    # what the Lock button does, under the server's lock
        finally:
            api.mutex.release()
        release.set()
        t.join(10)
        self.assertEqual(outcome, {"locked": True})       # the answer is dropped, not returned to a locked app
        self.assertFalse(api.status()["unlocked"])

    def test_locking_and_signing_straight_back_in_still_drops_the_old_answer(self):
        started, release = threading.Event(), threading.Event()

        def slow_fetch(prefix):
            started.set()
            release.wait(10)
            return ""

        api = Api(breach_fetch=slow_fetch, copy_fn=lambda t, s: True)
        signed_up(api)
        api.add_entry({"website": "x.com", "username": "u", "password": "Qm7#vT2!zLp9Xr4K"})
        outcome = {}

        def run():
            try:
                outcome["result"] = api.check_breaches()
            except Locked:
                outcome["locked"] = True

        t = threading.Thread(target=run)
        t.start()
        self.assertTrue(started.wait(5))
        with api.mutex:
            api.lock()
            self.assertTrue(api.login("a@b.co", PW)["ok"])
        release.set()
        t.join(10)
        self.assertEqual(outcome, {"locked": True})

    def test_a_cancelled_check_stops_asking(self):
        calls = []
        counts, failed = breach.check(["a", "b", "c"], fetch=lambda p: calls.append(p) or "", cancelled=lambda: True)
        self.assertEqual((counts, failed, calls), ({}, 3, []))

    def test_timeout_and_unreachable_service_give_a_clear_error(self):
        for exc in (breach.BreachCheckError("timeout"), breach.BreachCheckError("URLError")):
            def broken(prefix, exc=exc):
                raise exc
            api = Api(breach_fetch=broken, copy_fn=lambda t, s: True)
            signed_up(api, f"{id(exc)}@b.co")
            api.add_entry({"website": "x.com", "username": "u", "password": "Qm7#vT2!zLp9Xr4K"})
            r = api.check_breaches()
            self.assertFalse(r["ok"])
            self.assertIn("internet", r["error"])

    def test_edits_made_during_the_check_do_not_break_the_answer(self):
        holder = {}

        def fetch(prefix):
            holder["api"].delete_entry(holder["id"])      # the entry disappears while we wait
            return ""

        api = Api(breach_fetch=fetch, copy_fn=lambda t, s: True)
        holder["api"] = api
        signed_up(api)
        holder["id"] = api.add_entry({"website": "x.com", "username": "u", "password": "Qm7#vT2!zLp9Xr4K"})["id"]
        r = api.check_breaches()
        self.assertTrue(r["ok"])
        self.assertEqual(r["compromised"], {})


class TestSettingsThatFailToSave(DataDirTest):
    def setUp(self):
        super().setUp()
        self.api = Api(copy_fn=lambda t, s: True)
        signed_up(self.api)

    def test_a_failed_save_leaves_the_running_setting_unchanged(self):
        before = self.api._autolock_minutes()
        for error in (PermissionError("denied"), OSError(28, "No space left on device")):
            with mock.patch.object(storage, "save_users", side_effect=error):
                r = self.api.set_settings({"autolock_minutes": 10})
            self.assertFalse(r["ok"])
            self.assertEqual(self.api._autolock_minutes(), before)
        self.assertEqual(Api().users["a@b.co"].get("autolock_minutes"), None)   # nothing reached the disk

    def test_a_saved_setting_survives_a_restart(self):
        self.assertTrue(self.api.set_settings({"autolock_minutes": 10})["ok"])
        self.assertEqual(self.api._autolock_minutes(), 10)
        self.assertEqual(Api().users["a@b.co"]["autolock_minutes"], 10)

    def test_a_save_that_fails_midway_keeps_the_old_file(self):
        self.api.set_settings({"autolock_minutes": 2})
        with mock.patch("os.replace", side_effect=OSError("power cut")):
            self.assertFalse(self.api.set_settings({"autolock_minutes": 10})["ok"])
        self.assertEqual(Api().users["a@b.co"]["autolock_minutes"], 2)
        self.assertEqual(self.api._autolock_minutes(), 2)


if __name__ == "__main__":
    unittest.main()
    