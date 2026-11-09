"""The key scheme: key formats, wrapping, file permissions and crash-safe writes."""
import base64
import json
import os
import stat
import unittest
from unittest import mock

from tests.helpers import DataDirTest, read_bytes
from paksward import accounts, config, secretkey, storage, vaultkeys


class TestKeyFormat(unittest.TestCase):
    def test_round_trip_and_forgiving_input(self):
        raw = secretkey.generate()
        text = secretkey.format_key("PWSK", raw)
        self.assertEqual(secretkey.parse_key("PWSK", text), raw)
        self.assertEqual(secretkey.parse_key("PWSK", " " + text.lower().replace("-", " ") + "\n"), raw)

    def test_keys_are_160_random_bits_and_distinct(self):
        self.assertEqual(len(secretkey.generate()), 20)
        self.assertNotEqual(secretkey.generate(), secretkey.generate())

    def test_every_single_character_typo_is_caught(self):
        text = secretkey.format_key("PWRK", secretkey.generate())
        body = text.replace("-", "")[4:]
        for i in range(len(body)):
            swap = "A" if body[i] != "A" else "B"
            typo = "PWRK" + body[:i] + swap + body[i + 1:]
            with self.assertRaises(secretkey.KeyFormatError, msg=f"position {i}"):
                secretkey.parse_key("PWRK", typo)

    def test_a_secret_key_is_not_accepted_as_a_recovery_key(self):
        with self.assertRaises(secretkey.KeyFormatError):
            secretkey.parse_key("PWRK", secretkey.format_key("PWSK", secretkey.generate()))

    def test_garbage(self):
        for bad in ("", None, "PWSK", "PWSK-1111", "hello world"):
            with self.assertRaises(secretkey.KeyFormatError):
                secretkey.parse_key("PWSK", bad)


class TestWraps(unittest.TestCase):
    def setUp(self):
        self.vk, self.sk, self.rk = b"v" * 44, secretkey.generate(), secretkey.generate()
        self.rec = vaultkeys.build_wraps(self.vk, "a good login phrase 1", self.sk, self.rk)

    def test_password_and_secret_key_both_required(self):
        self.assertEqual(vaultkeys.unwrap_password(self.rec, "a good login phrase 1", self.sk), self.vk)
        self.assertIsNone(vaultkeys.unwrap_password(self.rec, "a good login phrase 1", secretkey.generate()))
        self.assertIsNone(vaultkeys.unwrap_password(self.rec, "a good password 2", self.sk))

    def test_recovery_key_works_alone_and_nothing_else_does(self):
        self.assertEqual(vaultkeys.unwrap_recovery(self.rec, self.rk), self.vk)
        self.assertIsNone(vaultkeys.unwrap_recovery(self.rec, self.sk))

    def test_record_uses_argon2id_and_stores_no_key_material_in_the_clear(self):
        self.assertEqual(self.rec["kdf"]["name"], "argon2id")
        self.assertGreaterEqual(self.rec["kdf"]["memory_kib"], 64 * 1024)
        dumped = json.dumps(self.rec)
        for raw in (self.sk, self.rk, self.vk):
            self.assertNotIn(base64.b64encode(raw).decode(), dumped)

    def test_each_wrap_gets_a_fresh_salt(self):
        again = vaultkeys.password_wrap(self.vk, "a good login phrase 1", self.sk)
        self.assertNotEqual(again["kdf"]["salt"], self.rec["kdf"]["salt"])

    def test_tampered_parameters_are_refused_not_obeyed(self):
        for field, value in (("memory_kib", 10 ** 9), ("iterations", 10 ** 6), ("lanes", 0),
                             ("name", "pbkdf2"), ("salt", "AAAA"), ("memory_kib", True)):
            rec = json.loads(json.dumps(self.rec))
            rec["kdf"][field] = value
            with self.assertRaises(vaultkeys.BadRecord, msg=field):
                vaultkeys.unwrap_password(rec, "a good login phrase 1", self.sk)

    def test_a_flipped_byte_in_the_wrap_fails_cleanly(self):
        rec = dict(self.rec, pw_wrap=self.rec["pw_wrap"][:-4] + "AAAA")
        self.assertIsNone(vaultkeys.unwrap_password(rec, "a good login phrase 1", self.sk))


class TestPermissions(DataDirTest):
    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_private_files_and_folders(self):
        accounts.create_account({}, "a@b.co", "Zebra-4-Quartz-Lantern-91")
        self.assertEqual(stat.S_IMODE(os.stat(config.SECRET_DIR).st_mode), 0o700)
        keyfile = os.path.join(config.SECRET_DIR, os.listdir(config.SECRET_DIR)[0])
        self.assertEqual(stat.S_IMODE(os.stat(keyfile).st_mode), 0o600)
        vault = os.path.join(config.VAULTS_DIR, os.listdir(config.VAULTS_DIR)[0])
        self.assertEqual(stat.S_IMODE(os.stat(vault).st_mode), 0o600)

    def test_no_temporary_files_are_left_behind(self):
        accounts.create_account({}, "a@b.co", "Zebra-4-Quartz-Lantern-91")
        for folder in (config.DATA_DIR, config.VAULTS_DIR, config.SECRET_DIR):
            self.assertFalse([n for n in os.listdir(folder) if n.startswith(".tmp-")], folder)

    def test_secret_key_is_stored_outside_the_data_folder(self):
        accounts.create_account({}, "a@b.co", "Zebra-4-Quartz-Lantern-91")
        self.assertFalse(os.path.commonpath([config.SECRET_DIR, config.DATA_DIR]) in (config.SECRET_DIR,))
        for root, _, files in os.walk(config.DATA_DIR):
            for name in files:
                with open(os.path.join(root, name), "rb") as f:
                    self.assertNotIn(b"PWSK", f.read())

    def test_writes_are_flushed_to_disk_before_the_swap(self):
        with mock.patch("os.fsync", wraps=os.fsync) as fsync:
            storage.atomic_write(os.path.join(config.DATA_DIR, "x.bin"), b"data")
        self.assertGreaterEqual(fsync.call_count, 1 if os.name == "nt" else 2)

    def test_failed_write_leaves_the_old_file_untouched(self):
        path = os.path.join(config.DATA_DIR, "x.bin")
        storage.atomic_write(path, b"old")
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                storage.atomic_write(path, b"new")
        self.assertEqual(read_bytes(path), b"old")
        self.assertFalse([n for n in os.listdir(config.DATA_DIR) if n.startswith(".tmp-")])


if __name__ == "__main__":
    unittest.main()
