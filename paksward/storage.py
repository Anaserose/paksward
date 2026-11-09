"""Reading and writing users.json and vault files, safely."""
import hashlib
import json
import os
import tempfile

from cryptography.fernet import Fernet, InvalidToken

from . import config


class VaultCorrupted(Exception):
    """Raised when a vault file exists but can't be decrypted or parsed."""


def make_private_dir(path: str):
    """Create a folder only the current user can enter (on systems that support permissions)."""
    os.makedirs(path, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def ensure_dirs():
    make_private_dir(config.DATA_DIR)
    make_private_dir(config.VAULTS_DIR)


def vault_path_for(email: str) -> str:
    return os.path.join(config.VAULTS_DIR, hashlib.sha256(email.lower().encode("utf-8")).hexdigest() + ".enc")


def atomic_write(path: str, data: bytes):
    """Write so that a crash leaves either the old file or the new one, never a mix.

    Data goes to a fresh private temporary file in the same folder, is flushed to disk, and is then
    swapped in. The temporary name is unpredictable and created exclusively, so another program
    cannot pre-plant a link there.
    """
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp-")        # created with mode 0600
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:                                                          # make the rename itself durable
        dfd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


def load_users() -> dict:
    if not os.path.exists(config.USERS_FILE):
        return {}
    with open(config.USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    if not isinstance(users, dict):
        raise ValueError("users.json is not an account list")
    return users


def save_users(users: dict):
    atomic_write(config.USERS_FILE, json.dumps(users, indent=2).encode("utf-8"))


def load_vault(fernet: Fernet, email: str) -> list:
    path = vault_path_for(email)
    if not os.path.isfile(path):
        raise VaultCorrupted("Your vault file is missing. Paksward will not create a new one over it. "
                             "If you use Dropbox or iCloud, wait for it to finish syncing, "
                             "or restore the file from a backup.")
    with open(path, "rb") as f:
        token = f.read()
    if not token:
        raise VaultCorrupted("Your vault file is empty. Paksward will not replace it. "
                             "Restore the file from a backup or your cloud service's version history.")
    unreadable = VaultCorrupted("Your vault file appears to be corrupted and couldn't be read. "
                                "Your password is correct, but the saved entries could not be loaded.")
    try:
        entries = json.loads(fernet.decrypt(token).decode("utf-8"))
    except (InvalidToken, ValueError) as exc:
        raise unreadable from exc
    if not isinstance(entries, list):
        raise unreadable
    return entries

def save_vault(fernet: Fernet, email: str, entries: list):
    atomic_write(vault_path_for(email), fernet.encrypt(json.dumps(entries).encode("utf-8")))
