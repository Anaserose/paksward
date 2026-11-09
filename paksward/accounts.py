"""Accounts: creating them, opening them, resetting passwords, and the login lockout (no UI).

Opening an account needs the master password AND the Secret Key kept on this device.
"""
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

from . import devicekey, secretkey, vaultkeys
from .config import LOCKOUT_HOURS, MAX_LOGIN_ATTEMPTS
from .storage import save_users, save_vault

NEED_SECRET = "need_secret"          # returned by open_account when the Secret Key is not on this device


def create_account(users, email, password):
    """Make a new account. Returns (vault_key, secret_key_text, recovery_key_text)."""
    vault_key = Fernet.generate_key()
    secret_raw, recovery_raw = secretkey.generate(), secretkey.generate()
    record = {"email": email, **vaultkeys.build_wraps(vault_key, password, secret_raw, recovery_raw)}
    # The record is written last: a crash earlier leaves unused files, never an account that cannot open.
    devicekey.save(email, secret_raw)
    save_vault(Fernet(vault_key), email, [])
    users[email.lower()] = record
    save_users(users)
    return (vault_key,
            secretkey.format_key(secretkey.SECRET_PREFIX, secret_raw),
            secretkey.format_key(secretkey.RECOVERY_PREFIX, recovery_raw))


def open_account(users, email, password, secret_text=None):
    """Try to open an account.

    Returns the vault key on success, None for a wrong password/Secret Key or an unknown account, or
    NEED_SECRET when this device does not have the account's Secret Key and none was given.
    Raises vaultkeys.BadRecord if the stored record is damaged.
    """
    record = users.get(email.lower())
    if not record:
        return None
    secret_raw = devicekey.load(email)
    if secret_text:
        try:
            secret_raw = secretkey.parse_key(secretkey.SECRET_PREFIX, secret_text)
        except secretkey.KeyFormatError:
            return None
    if secret_raw is None:
        return NEED_SECRET
    key = vaultkeys.unwrap_password(record, password, secret_raw)
    if key is None:
        return None
    if secret_text:
        devicekey.save(email, secret_raw)         # remember it on this device from now on
    return key


def open_with_recovery(users, email, recovery_text):
    """The vault key for a Recovery Key, else None."""
    record = users.get(email.lower())
    if not record:
        return None
    try:
        raw = secretkey.parse_key(secretkey.RECOVERY_PREFIX, recovery_text)
    except secretkey.KeyFormatError:
        return None
    return vaultkeys.unwrap_recovery(record, raw)


def reset_password(users, email, new_password, vault_key: bytes):
    """Set a new master password after recovery. Also issues a new Secret Key, because this device may
    not have the old one. Returns the new Secret Key as text, to show once."""
    secret_raw = secretkey.generate()
    devicekey.save(email, secret_raw)                 # device key first, account record last
    fresh = {**users[email.lower()], **vaultkeys.password_wrap(vault_key, new_password, secret_raw),
             "failed_attempts": 0, "lockout_until": None}
    save_users({**users, email.lower(): fresh})
    users[email.lower()] = fresh
    return secretkey.format_key(secretkey.SECRET_PREFIX, secret_raw)


def change_password(users, email, new_password, vault_key: bytes, secret_raw: bytes):
    """Change the master password while signed in; the Secret Key stays the same."""
    fresh = {**users[email.lower()], **vaultkeys.password_wrap(vault_key, new_password, secret_raw)}
    save_users({**users, email.lower(): fresh})
    users[email.lower()] = fresh


def device_secret(email):
    """The Secret Key on this device as display text, or None."""
    raw = devicekey.load(email)
    return None if raw is None else secretkey.format_key(secretkey.SECRET_PREFIX, raw)


def device_secret_raw(email):
    return devicekey.load(email)


def new_recovery_key(users, email, vault_key: bytes):
    """Replace the Recovery Key (the old one stops working). Returns the new one as text."""
    raw = secretkey.generate()
    fresh = {**users[email.lower()], **vaultkeys.recovery_wrap(vault_key, raw)}
    save_users({**users, email.lower(): fresh})
    users[email.lower()] = fresh
    return secretkey.format_key(secretkey.RECOVERY_PREFIX, raw)


# --- lockout (a convenience against someone sitting at this app; it cannot stop offline guessing) ---

def lockout_remaining(record):
    until = record.get("lockout_until")
    if not until:
        return None
    remaining = datetime.fromisoformat(until) - datetime.now(timezone.utc)
    return remaining if remaining.total_seconds() > 0 else None


def format_remaining(delta):
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes = rem // 60
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def record_failed_attempt(users, email):
    record = users[email.lower()]
    record["failed_attempts"] = record.get("failed_attempts", 0) + 1
    if record["failed_attempts"] >= MAX_LOGIN_ATTEMPTS:
        record["lockout_until"] = (datetime.now(timezone.utc) + timedelta(hours=LOCKOUT_HOURS)).isoformat()
    save_users(users)


def clear_failed_attempts(users, email):
    record = users[email.lower()]
    record["failed_attempts"] = 0
    record["lockout_until"] = None
    save_users(users)


def clear_lockout_if_expired(users, email):
    record = users[email.lower()]
    if record.get("lockout_until") and lockout_remaining(record) is None:
        clear_failed_attempts(users, email)
