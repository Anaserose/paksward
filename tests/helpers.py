"""Shared test setup for the v3 package tests."""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from paksward import config  # noqa: E402



def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Clock:
    """A clock the test can move forward."""
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class DataDirTest(unittest.TestCase):
    """Each test gets an empty private data folder (config paths are redirected to it)."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = (config.USERS_FILE, config.VAULTS_DIR, config.DATA_DIR, config.SECRET_DIR)
        config.USERS_FILE = os.path.join(self.tmp, "users.json")
        config.VAULTS_DIR = os.path.join(self.tmp, "vaults")
        config.DATA_DIR = self.tmp
        config.SECRET_DIR = os.path.join(self.tmp + "-device")      # outside the data folder, as in real use
        os.makedirs(config.VAULTS_DIR)
        self.addCleanup(self._restore)

    def _restore(self):
        config.USERS_FILE, config.VAULTS_DIR, config.DATA_DIR, config.SECRET_DIR = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.tmp + "-device", ignore_errors=True)
