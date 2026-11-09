"""Where this device keeps the Secret Key, outside the vault folder.

One small private file per account. Anyone who copies only the data folder gets an encrypted vault
they cannot open, however weak the master password is.
"""
import hashlib
import os

from . import config, secretkey
from .storage import atomic_write, make_private_dir


def _path(email: str) -> str:
    return os.path.join(config.SECRET_DIR, hashlib.sha256(email.lower().encode("utf-8")).hexdigest() + ".key")


def load(email: str):
    """The stored Secret Key as bytes, or None if this device has none (or the file is damaged)."""
    try:
        with open(_path(email), "r", encoding="ascii") as f:
            return secretkey.parse_key(secretkey.SECRET_PREFIX, f.read())
    except (OSError, UnicodeDecodeError, secretkey.KeyFormatError):
        return None


def save(email: str, raw: bytes):
    make_private_dir(config.SECRET_DIR)
    atomic_write(_path(email), (secretkey.format_key(secretkey.SECRET_PREFIX, raw) + "\n").encode("ascii"))
