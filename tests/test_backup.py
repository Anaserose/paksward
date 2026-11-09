"""Backup and restore: nothing secret inside, never overwrites, rejects junk, works on a fresh computer."""
import base64
import json
import os
import shutil
import unittest

from tests.helpers import DataDirTest, read_bytes
from paksward import backup, config, storage
from paksward.api import Api, Locked

PW = "Zebra-4-Quartz-Lantern-91"


class TestBackup(DataDirTest):
    def setUp(self):
        super().setUp()
        self.api = Api(copy_fn=lambda t, s: True)
        r = self.api.register("a@b.co", PW, PW)
        self.secret, self.recovery = r["kit"]["secret_key"], r["kit"]["recovery_key"]
        self.api.add_entry({"website": "github.com", "username": "ana", "password": "Qm7#vT2!zLp9Xr4K"})
        self.api.add_entry({"website": "bank.com", "username": "ana", "password": "Hy3$wN8!cRd5Ts2J"})
        self.exported = self.api.export_backup()

    def wipe_computer(self):
        """Pretend this is a new computer: no account, no vault, no Secret Key."""
        self.api.lock()
        shutil.rmtree(config.VAULTS_DIR)
        os.makedirs(config.VAULTS_DIR)
        os.remove(config.USERS_FILE)
        shutil.rmtree(config.SECRET_DIR)
        return Api(copy_fn=lambda t, s: True)

    def test_export_needs_an_unlocked_vault(self):
        self.api.lock()
        with self.assertRaises(Locked):
            self.api.export_backup()

    def test_export_has_a_name_and_the_data(self):
        self.assertTrue(self.exported["ok"])
        self.assertRegex(self.exported["filename"], r"^paksward-backup-\d{4}-\d{2}-\d{2}\.pkbackup$")

    def test_the_backup_contains_no_password_key_or_plaintext(self):
        text = self.exported["data"]
        for secret in (PW, self.secret, self.recovery, "Qm7#vT2!zLp9Xr4K", "github.com", "bank.com", "ana"):
            self.assertNotIn(secret, text)
        raw = base64.b32decode(self.secret.replace("-", "")[4:36])
        self.assertNotIn(base64.b64encode(raw).decode(), text)
        data = json.loads(text)
        self.assertNotIn("failed_attempts", data["account"])        # lockout state is not carried over
        self.assertNotIn("lockout_until", data["account"])

    def test_restore_on_a_new_computer_opens_with_password_and_secret_key(self):
        text = self.exported["data"]
        fresh = self.wipe_computer()
        self.assertTrue(fresh.restore_backup(text)["ok"])
        self.assertTrue(fresh.login("a@b.co", PW)["need_secret"])            # the Secret Key is not in the backup
        self.assertTrue(fresh.login("a@b.co", PW, self.secret)["ok"])
        self.assertEqual({e["website"] for e in fresh.list_entries()}, {"github.com", "bank.com"})

    def test_restore_opens_with_the_recovery_key_too(self):
        fresh = self.wipe_computer()
        fresh.restore_backup(self.exported["data"])
        fresh.recover_start("a@b.co")
        self.assertTrue(fresh.recover_verify(self.recovery)["ok"])

    def test_restore_never_overwrites_an_existing_account(self):
        before_users, before_vault = read_bytes(config.USERS_FILE), read_bytes(storage.vault_path_for("a@b.co"))
        r = self.api.restore_backup(self.exported["data"])
        self.assertFalse(r["ok"])
        self.assertIn("already exists", r["error"])
        self.assertEqual(read_bytes(config.USERS_FILE), before_users)
        self.assertEqual(read_bytes(storage.vault_path_for("a@b.co")), before_vault)

    def test_a_stray_vault_file_is_not_overwritten_either(self):
        text = self.exported["data"]
        fresh = self.wipe_computer()
        storage.atomic_write(storage.vault_path_for("a@b.co"), b"something else")
        self.assertFalse(fresh.restore_backup(text)["ok"])
        self.assertEqual(read_bytes(storage.vault_path_for("a@b.co")), b"something else")

    def test_junk_and_tampered_files_are_rejected_and_change_nothing(self):
        good = json.loads(self.exported["data"])
        bad_files = ["", "not json", "[]", "{}", json.dumps({**good, "format": "other"}),
                     json.dumps({**good, "email": "nope"}), json.dumps({**good, "vault": "!!!"}),
                     json.dumps({**good, "vault": base64.b64encode(b"hello").decode()}),
                     json.dumps({**good, "account": {**good["account"], "kdf": {**good["account"]["kdf"], "memory_kib": 10 ** 9}}}),
                     json.dumps({**good, "account": {k: v for k, v in good["account"].items() if k != "pw_wrap"}}),
                     "x" * (backup.MAX_BYTES + 1), None, 5]
        fresh = self.wipe_computer()
        for text in bad_files:
            r = fresh.restore_backup(text)
            self.assertFalse(r["ok"], repr(text)[:60])
        self.assertEqual(fresh.users, {})
        self.assertEqual(os.listdir(config.VAULTS_DIR), [])

    def test_a_restore_that_cannot_be_saved_leaves_nothing_half_done(self):
        from unittest import mock
        text = self.exported["data"]
        fresh = self.wipe_computer()
        with mock.patch.object(backup.storage, "save_users", side_effect=OSError("disk full")):
            r = fresh.restore_backup(text)
        self.assertFalse(r["ok"])
        self.assertEqual(fresh.users, {})

    def test_export_fails_clearly_if_the_vault_file_is_gone(self):
        os.remove(storage.vault_path_for("a@b.co"))
        r = self.api.export_backup()
        self.assertFalse(r["ok"])
        self.assertNotIn("data", r)


if __name__ == "__main__":
    unittest.main()