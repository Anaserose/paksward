"""How the vault key is protected.

The vault is encrypted with one random vault key. That key is stored twice, each copy encrypted
("wrapped") under a different key, and nothing else about it is stored:

  password wrap   key = HKDF( Argon2id(master password) + Secret Key )
  recovery wrap   key = HKDF( Recovery Key )

Guessing the master password from a copy of the files is impossible without the Secret Key, which
is 160 random bits kept off the data folder. The Recovery Key is 160 random bits too. Argon2id makes
each password guess cost 64 MiB of memory, which matters for anyone who obtains both.
"""
import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FORMAT = 3
DEFAULT_KDF = {"name": "argon2id", "iterations": 3, "lanes": 4, "memory_kib": 65536}
# Limits for values read back from users.json, so a tampered file cannot make the app allocate
# gigabytes or spin for minutes.
_LIMITS = {"iterations": (1, 10), "lanes": (1, 16), "memory_kib": (8 * 1024, 1024 * 1024)}


class BadRecord(ValueError):
    """The account record holds values this version will not use."""


def _kdf_params(kdf: dict) -> dict:
    if not isinstance(kdf, dict) or kdf.get("name") != "argon2id":
        raise BadRecord("unsupported key derivation")
    for k, (lo, hi) in _LIMITS.items():
        if not isinstance(kdf.get(k), int) or isinstance(kdf.get(k), bool) or not lo <= kdf[k] <= hi:
            raise BadRecord(f"{k} out of range")
    try:
        salt = base64.b64decode(kdf["salt"], validate=True)
    except (KeyError, ValueError, TypeError):
        raise BadRecord("bad salt") from None
    if len(salt) < 16:
        raise BadRecord("salt too short")
    return {"salt": salt, "iterations": kdf["iterations"], "lanes": kdf["lanes"], "memory_cost": kdf["memory_kib"]}


def _stretch(password: str, kdf: dict) -> bytes:
    return Argon2id(length=32, **_kdf_params(kdf)).derive(password.encode("utf-8"))


def _fernet_key(material: bytes, info: bytes) -> bytes:
    return base64.urlsafe_b64encode(HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(material))


def _password_key(password: str, secret_raw: bytes, kdf: dict) -> bytes:
    return _fernet_key(_stretch(password, kdf) + secret_raw, b"paksward/v3/password-wrap")


def _recovery_key(recovery_raw: bytes) -> bytes:
    return _fernet_key(recovery_raw, b"paksward/v3/recovery-wrap")


def new_kdf() -> dict:
    return {**DEFAULT_KDF, "salt": base64.b64encode(os.urandom(16)).decode()}


def password_wrap(vault_key: bytes, password: str, secret_raw: bytes) -> dict:
    """Fresh salt, fresh password wrap. Returns the two record fields it replaces."""
    kdf = new_kdf()
    return {"kdf": kdf, "pw_wrap": Fernet(_password_key(password, secret_raw, kdf)).encrypt(vault_key).decode()}


def recovery_wrap(vault_key: bytes, recovery_raw: bytes) -> dict:
    return {"rec_wrap": Fernet(_recovery_key(recovery_raw)).encrypt(vault_key).decode()}


def build_wraps(vault_key: bytes, password: str, secret_raw: bytes, recovery_raw: bytes) -> dict:
    return {"format": FORMAT, **password_wrap(vault_key, password, secret_raw), **recovery_wrap(vault_key, recovery_raw)}


def unwrap_password(record: dict, password: str, secret_raw: bytes):
    """The vault key, or None if the password or Secret Key is wrong. Raises BadRecord for a damaged record."""
    key = _password_key(password, secret_raw, record.get("kdf"))
    try:
        return Fernet(key).decrypt(record["pw_wrap"].encode("ascii"))
    except (InvalidToken, KeyError, ValueError, AttributeError):
        return None


def unwrap_recovery(record: dict, recovery_raw: bytes):
    try:
        return Fernet(_recovery_key(recovery_raw)).decrypt(record["rec_wrap"].encode("ascii"))
    except (InvalidToken, KeyError, ValueError, AttributeError):
        return None
