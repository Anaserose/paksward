"""Backup and restore of one account.

A backup file holds exactly what is already on disk for the account: the encrypted vault and the small
account record (salt and the two wrapped copies of the vault key). It contains no password, no Secret Key
and no Recovery Key, so it is as safe to store as the data folder is, and just as useless without the keys.
Restoring never overwrites an existing account.
"""
import base64
import json
import os
from datetime import datetime, timezone

from . import storage, vaultkeys
from .validation import is_valid_email

FORMAT = "paksward-backup-1"
MAX_BYTES = 3_000_000
_ACCOUNT_FIELDS = ("format", "kdf", "pw_wrap", "rec_wrap", "autolock_minutes")


class BackupError(Exception):
    """The backup file cannot be used. The message is safe to show."""


def create(email: str, record: dict) -> str:
    """Backup file text for the account. Raises BackupError if its vault file cannot be read."""
    path = storage.vault_path_for(email)
    try:
        with open(path, "rb") as f:
            ciphertext = f.read()
    except OSError:
        raise BackupError("The vault file could not be read, so no backup was made.") from None
    if not ciphertext:
        raise BackupError("The vault file is empty, so no backup was made.")
    account = {k: record[k] for k in _ACCOUNT_FIELDS if k in record}
    return json.dumps({"format": FORMAT, "email": email, "account": account,
                       "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "vault": base64.b64encode(ciphertext).decode("ascii")})


def parse(text: str):
    """Check a backup file and return (email, account_record, ciphertext). Raises BackupError."""
    bad = BackupError("That is not a valid Paksward backup file.")
    if not isinstance(text, str) or len(text) > MAX_BYTES:
        raise BackupError("That file is too large to be a Paksward backup.")
    try:
        data = json.loads(text)
        email, account, vault = data["email"], data["account"], data["vault"]
        if data.get("format") != FORMAT or not isinstance(account, dict) or not isinstance(email, str):
            raise bad
        ciphertext = base64.b64decode(vault, validate=True)
    except (ValueError, KeyError, TypeError):
        raise bad from None
    if not is_valid_email(email) or len(email) > 254 or not ciphertext.startswith(b"gAAAA"):
        raise bad
    account = {k: account[k] for k in _ACCOUNT_FIELDS if k in account}
    try:                                                   # same limits the app applies to any account record
        vaultkeys._kdf_params(account.get("kdf"))
    except vaultkeys.BadRecord:
        raise bad from None
    if not all(isinstance(account.get(k), str) for k in ("pw_wrap", "rec_wrap")) or account.get("format") != vaultkeys.FORMAT:
        raise bad
    return email, account, ciphertext


def restore(users: dict, text: str) -> str:
    """Add the backed-up account to this computer. Returns its email. Never replaces an existing account."""
    email, account, ciphertext = parse(text)
    if email.lower() in users:
        raise BackupError("An account with this email already exists on this computer, so nothing was restored. "
                          "Move or delete the existing data folder first if you really want to replace it.")
    path = storage.vault_path_for(email)
    if os.path.exists(path):
        raise BackupError("A vault file for this email already exists on this computer, so nothing was restored.")
    storage.ensure_dirs()
    storage.atomic_write(path, ciphertext)                 # vault first, account record last
    users[email.lower()] = {"email": email, **account}
    try:
        storage.save_users(users)
    except OSError:
        users.pop(email.lower(), None)
        raise
    return email