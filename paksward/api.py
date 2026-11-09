"""The backend the web interface talks to. One instance holds one signed-in session.

Every public method returns plain JSON-able data. Expected problems come back as
{"ok": False, "error": "..."}; a locked vault raises Locked, which the server turns into
{"ok": False, "locked": True}. Passwords leave this class only through get_entry().
"""
import threading
import time

from cryptography.fernet import Fernet

from . import accounts, backup, breach, clipboard, entries as E, generator, storage, strength, vaultkeys, watchtower
from .config import AUTOLOCK_CHOICES, DEFAULT_AUTOLOCK_MINUTES, MAX_LOGIN_ATTEMPTS
from .validation import is_valid_email, password_problem


MAX_EMAIL = 254
MAX_PASSWORD = 1024
MAX_FIELD = 500
RECOVERY_SECONDS = 600


class Locked(Exception):
    """The vault is locked (never opened, locked by the user, or locked by inactivity)."""


PUBLIC = (
    "status", "login", "register", "recover_start", "recover_verify", "recover_reset", "lock", "touch",
    "get_secret_key", "new_recovery_key", "change_password",
    "list_entries", "get_entry", "add_entry", "update_entry", "delete_entry", "set_favorite", "copy_text",
    "check_strength", "generate", "security_report", "check_breaches","export_backup", "restore_backup", "get_settings", "set_settings",
)


def _ok(**kw):
    return {"ok": True, **kw}


def _bad(error, **kw):
    return {"ok": False, "error": error, **kw}


class Api:
    SLOW_CALLS = ("check_breaches",)

    def __init__(self, clock=time.monotonic, copy_fn=None, breach_fetch=None):
        self._clock = clock
        self._breach_fetch = breach_fetch or breach.fetch_range
        self._copy = copy_fn or clipboard.copy_and_schedule_clear
        self.mutex = threading.Lock()
        self.users = storage.load_users()      # raises ValueError if users.json is corrupt; the caller must handle it
        self._reset_session()
        self._recovery = None

    # ---- session helpers -------------------------------------------------
    def _reset_session(self):
        self.email = self.vault_key = self.fernet = None
        self.entries = []
        self._last_touch = 0.0

    def _record(self):
        return self.users[self.email.lower()]

    def _autolock_minutes(self):
        m = self._record().get("autolock_minutes", DEFAULT_AUTOLOCK_MINUTES)
        return m if m in AUTOLOCK_CHOICES else DEFAULT_AUTOLOCK_MINUTES

    def _require(self):
        """Raise Locked unless the vault is open and not idle. Counts as activity."""
        if not self.fernet:
            raise Locked()
        limit = self._autolock_minutes()
        if limit and self._clock() - self._last_touch > limit * 60:
            self._reset_session()
            raise Locked()
        self._last_touch = self._clock()

    def _persist(self):
        storage.save_vault(self.fernet, self.email, self.entries)

    def _enter(self, email, vault_key):
        fernet = Fernet(vault_key)
        try:
            loaded = storage.load_vault(fernet, email)
        except storage.VaultCorrupted as exc:
            return _bad(str(exc))
        E.normalize(loaded)        # in memory only; written back the next time the user saves
        self.email, self.vault_key, self.fernet, self.entries = email, vault_key, fernet, loaded
        self._last_touch = self._clock()
        return _ok(email=email)

    def _find(self, entry_id):
        for e in self.entries:
            if e["id"] == entry_id:
                return e
        return None

    # ---- account ---------------------------------------------------------
    def status(self):
        if self.fernet:
            try:
                self._require()
            except Locked:
                pass
        return {"unlocked": bool(self.fernet), "email": self.email, "preview": False}

    def login(self, email, password, secret_key=None):
        email = (email or "").strip()
        password = password or ""
        if not email or not password:
            return _bad("Please enter both an email and a password.")
        if not is_valid_email(email) or len(email) > MAX_EMAIL or len(password) > MAX_PASSWORD:
            return _bad("Please enter a valid email address.")
        record = self.users.get(email.lower())
        if not record:
            return _bad("No account found with this email.")
        accounts.clear_lockout_if_expired(self.users, email)
        remaining = accounts.lockout_remaining(record)
        if remaining:
            return _bad(f"Too many failed attempts. Try again in {accounts.format_remaining(remaining)}.")
        try:
            opened = accounts.open_account(self.users, email, password, (secret_key or "").strip() or None)
        except (vaultkeys.BadRecord, OSError):
            self.users = storage.load_users()
            return _bad("This account's saved data could not be read or saved, so nothing was changed.")
        if opened == accounts.NEED_SECRET:
            return _bad("This device doesn't have the Secret Key for this account. Enter it to continue.",
                        need_secret=True)
        if opened is None:
            accounts.record_failed_attempt(self.users, email)
            left = MAX_LOGIN_ATTEMPTS - self.users[email.lower()]["failed_attempts"]
            what = "password or Secret Key" if secret_key else "password"
            if left <= 0:
                return _bad(f"Incorrect {what}. Account locked for 24 hours.")
            return _bad(f"Incorrect {what}. {left} attempt(s) left before a 24-hour lock.")
        accounts.clear_failed_attempts(self.users, email)
        return self._enter(email, opened)

    def register(self, email, password, confirm):
        email = (email or "").strip()
        if not all([email, password, confirm]):
            return _bad("Please fill in every field before creating your account.")
        if not is_valid_email(email) or len(email) > MAX_EMAIL:
            return _bad("Please enter a valid email address.")
        problem = password_problem(password)
        if problem or len(password) > MAX_PASSWORD:
            return _bad(problem or "That password is too long.")
        if password != confirm:
            return _bad("Passwords do not match.")
        if email.lower() in self.users:
            return _bad("An account with this email already exists.")
        try:
            key, secret_text, recovery_text = accounts.create_account(self.users, email, password)
        except OSError:
            self.users = storage.load_users()
            return _bad("Something went wrong. Your account was not created.")
        result = self._enter(email, key)
        if result["ok"]:
            result["kit"] = {"secret_key": secret_text, "recovery_key": recovery_text}
        return result

    def recover_start(self, email):
        email = (email or "").strip()
        record = self.users.get(email.lower())
        if not record:
            return _bad("No account found for this email.")
        accounts.clear_lockout_if_expired(self.users, email)
        remaining = accounts.lockout_remaining(record)
        if remaining:
            return _bad(f"This account is locked. Try again in {accounts.format_remaining(remaining)}.")
        self._recovery = {"email": email, "key": None, "started": self._clock()}
        return _ok()
    def _live_recovery(self):
        """The recovery in progress, or None if there is none, it timed out, or the account has been locked since."""
        r = self._recovery
        if r and self._clock() - r["started"] > RECOVERY_SECONDS:
            self._recovery = r = None                      # also forgets the decrypted vault key
        if r:
            record = self.users.get(r["email"].lower())
            if not record or accounts.lockout_remaining(record):
                self._recovery = r = None
        return r

    def recover_verify(self, recovery_key):
        r = self._live_recovery()
        if not r:
            return _bad("Recovery timed out or the account is locked. Start again from the beginning.")
        if not recovery_key or len(recovery_key) > MAX_PASSWORD:
            return _bad("Please enter your Recovery Key.")
        key = accounts.open_with_recovery(self.users, r["email"], recovery_key)
        if key is None:
            accounts.record_failed_attempt(self.users, r["email"])
            left = MAX_LOGIN_ATTEMPTS - self.users[r["email"].lower()]["failed_attempts"]
            if left <= 0:
                self._recovery = None
                return _bad("Too many wrong attempts. Locked for 24 hours.")
            return _bad(f"That Recovery Key doesn't match. {left} attempt(s) left.")
        accounts.clear_failed_attempts(self.users, r["email"])
        r["key"] = key
        return _ok()

    def recover_reset(self, password, confirm):
        r = self._live_recovery()
        if not r or not r["key"]:
            return _bad("Verify your Recovery Key first (recovery sessions last %d minutes)." % (RECOVERY_SECONDS // 60))
        problem = password_problem(password)
        if problem or len(password) > MAX_PASSWORD:
            return _bad(problem or "That password is too long.")
        if password != confirm:
            return _bad("Passwords do not match.")
        try:
            secret_text = accounts.reset_password(self.users, r["email"], password, r["key"])
        except OSError:
            self.users = storage.load_users()
            return _bad("Something went wrong. Your password was not changed.")
        key, email, self._recovery = r["key"], r["email"], None
        result = self._enter(email, key)
        if result["ok"]:
            result["kit"] = {"secret_key": secret_text}      # the Secret Key was reissued: show it once
        return result

    # ---- keys and password (signed in) -----------------------------------
    def get_secret_key(self):
        self._require()
        text = accounts.device_secret(self.email)
        return _ok(secret_key=text) if text else _bad("This device has no Secret Key for the account.")

    def new_recovery_key(self):
        self._require()
        try:
            return _ok(recovery_key=accounts.new_recovery_key(self.users, self.email, self.vault_key))
        except OSError:
            self.users = storage.load_users()
            return _bad("Something went wrong. Your Recovery Key was not changed.")

    def change_password(self, current, new, confirm):
        self._require()
        opened = accounts.open_account(self.users, self.email, current or "")
        if opened is None or opened == accounts.NEED_SECRET:
            return _bad("Your current password is not correct.")
        problem = password_problem(new)
        if problem or len(new) > MAX_PASSWORD:
            return _bad(problem or "That password is too long.")
        if new != confirm:
            return _bad("Passwords do not match.")
        try:
            accounts.change_password(self.users, self.email, new, self.vault_key, accounts.device_secret_raw(self.email))
        except OSError:
            self.users = storage.load_users()
            return _bad("Something went wrong. Your password was not changed.")
        return _ok()

    def lock(self):
        self._reset_session()
        self._recovery = None
        return _ok()

    def touch(self):
        """The page calls this when the user is active, so reading a long entry doesn't trigger auto-lock."""
        self._require()
        return _ok()

    # ---- entries ---------------------------------------------------------
    def list_entries(self):
        self._require()
        reuse = watchtower.reuse_counts(self.entries)
        return [watchtower.entry_meta(e, reuse.get(e["id"], 1)) for e in self.entries]

    def get_entry(self, entry_id):
        self._require()
        e = self._find(entry_id)
        return _ok(entry=dict(e)) if e else _bad("Entry not found.")

    @staticmethod
    def _clean(data):
        d = data if isinstance(data, dict) else {}
        out = {"website": str(d.get("website", "")).strip()[:MAX_FIELD], "username": str(d.get("username", "")).strip()[:MAX_FIELD],
               "password": str(d.get("password", ""))[:MAX_PASSWORD], "favorite": bool(d.get("favorite")),
               "category": d.get("category") if d.get("category") in E.CATEGORIES else "Other"}
        if not (out["website"] and out["username"] and out["password"]):
            return None
        return out

    def add_entry(self, data):
        self._require()
        d = self._clean(data)
        if not d:
            return _bad("Website, username and password are required.")
        entry = {"id": E.new_id(), **d, "updated_at": E.now_iso()}
        self.entries.append(entry)
        try:
            self._persist()
        except OSError:
            self.entries.remove(entry)
            return _bad("Could not save to disk. Check free space and folder permissions.")
        return _ok(id=entry["id"])

    def update_entry(self, entry_id, data):
        self._require()
        e = self._find(entry_id)
        if not e:
            return _bad("Entry not found.")
        d = self._clean(data)
        if not d:
            return _bad("Website, username and password are required.")
        before = dict(e)
        if d["password"] != e["password"]:
            e["updated_at"] = E.now_iso()
        e.update(d)
        try:
            self._persist()
        except OSError:
            e.clear()
            e.update(before)
            return _bad("Could not save to disk. Check free space and folder permissions.")
        return _ok()

    def set_favorite(self, entry_id, value):
        self._require()
        e = self._find(entry_id)
        if not e:
            return _bad("Entry not found.")
        old = e["favorite"]
        e["favorite"] = bool(value)
        try:
            self._persist()
        except OSError:
            e["favorite"] = old
            return _bad("Could not save to disk.")
        return _ok()

    def delete_entry(self, entry_id):
        self._require()
        e = self._find(entry_id)
        if not e:
            return _bad("Entry not found.")
        idx = self.entries.index(e)
        del self.entries[idx]
        try:
            self._persist()
        except OSError:
            self.entries.insert(idx, e)
            return _bad("Could not save to disk.")
        return _ok()

    # ---- tools -----------------------------------------------------------
    def copy_text(self, text, clear_after=0):
        self._require()
        ok = self._copy(str(text), int(clear_after or 0))
        return _ok() if ok else _bad("The system clipboard is not available.")

    def check_strength(self, password):
        return strength.check_strength(password or "")

    def generate(self, options=None):
        return generator.generate(options if isinstance(options, dict) else {})

    def security_report(self):
        self._require()
        return watchtower.security_report(self.entries)

    def check_breaches(self):
        """Online and opt-in (the page asks first). Only 5-character fingerprint prefixes leave this computer.

        The network part can take many seconds, so the shared lock is held only to read the passwords and,
        afterwards, to build the answer. Locking the vault meanwhile works at once and the answer is dropped.
        """
        with self.mutex:
            self._require()
            session, snapshot = self.vault_key, [(e["id"], e["password"]) for e in self.entries]
        counts, failed = breach.check([pw for _, pw in snapshot], fetch=self._breach_fetch,
                                      cancelled=lambda: self.vault_key is not session)
        with self.mutex:
            self._require()
            if self.vault_key is not session:      # locked (and maybe unlocked again) while we were waiting
                raise Locked()
            self._last_touch = self._clock()       # a slow network check is not inactivity
            if snapshot and not counts:
                return _bad("Could not reach the breach service. Check your internet connection and try again. "
                            "Nothing was changed.")
            still_here = {e["id"] for e in self.entries}
            found = {i: counts[pw] for i, pw in snapshot if i in still_here and counts.get(pw, 0) > 0}
            return _ok(checked=sum(pw in counts for _, pw in snapshot), failed=failed, compromised=found)

    def export_backup(self):
        """The text of an encrypted backup file for the signed-in account (no password or keys inside)."""
        self._require()
        try:
            text = backup.create(self.email, self._record())
        except backup.BackupError as exc:
            return _bad(str(exc))
        return _ok(filename="paksward-backup-%s.pkbackup" % time.strftime("%Y-%m-%d"), data=text)

    def restore_backup(self, text):
        """Add a backed-up account to this computer (works while signed out). Never overwrites an account."""
        try:
            email = backup.restore(self.users, text)
        except backup.BackupError as exc:
            return _bad(str(exc))
        except OSError:
            self.users = storage.load_users()
            return _bad("Something went wrong while restoring, so nothing was changed.")
        return _ok(email=email)
    

    def get_settings(self):
        self._require()
        return _ok(settings={"autolock_minutes": self._autolock_minutes()})

    def set_settings(self, settings):
        self._require()
        m = (settings or {}).get("autolock_minutes")
        if m is not None:
            if m not in AUTOLOCK_CHOICES:
                return _bad("Choose Off, 2, 5 or 10 minutes.")
            key = self.email.lower()
            updated = {**self.users[key], "autolock_minutes": m}      # change a copy; keep it only if it was saved
            try:
                storage.save_users({**self.users, key: updated})
            except OSError:
                return _bad("Could not save settings.")
            self.users[key] = updated
        return _ok()
