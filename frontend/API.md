# Paksward UI ↔ Python API

The page calls these methods by name. When Paksward is running, they are `POST /api/<name>` requests
(body `{"args":[...]}`, header `X-Paksward-Token`) answered by `paksward/api.py`. When the page is opened
from `dev/preview.html`, the same names are answered by `dev/mock_api.js` with sample data.

Failures come back as `{ok:false, error:"message shown to the user"}`. A vault that is locked (by the
user or by inactivity) answers `{ok:false, locked:true}`, and the page returns to the login screen.

**Rule: a password leaves Python only through `get_entry`, one entry at a time.**
Lists, the dashboard and strength labels carry no secrets.

| Method | Returns |
|---|---|
| `status()` | `{unlocked, email, preview}` |
| `login(email, password, secret_key?)` | `{ok, email, kit?}`; `{ok:false, need_secret:true}` when this device lacks the Secret Key. 5 attempts, then a 24 hour lock |
| `register(email, pw, pw_confirm)` | `{ok, email, kit:{secret_key, recovery_key}}` |
| `recover_start(email)` / `recover_verify(recovery_key)` / `recover_reset(pw, pw_confirm)` | `{ok}` / `{ok}` / `{ok, email, kit:{secret_key[, recovery_key]}}` |
| `get_secret_key()` / `new_recovery_key()` / `change_password(current, new, confirm)` | `{ok, secret_key}` / `{ok, recovery_key}` / `{ok}` |
| `lock()` | `{ok}`; clears keys and entries from memory |
| `touch()` | `{ok}`; tells Python the user is active (resets the idle timer) |
| `list_entries()` | `[{id, website, username, category, favorite, updated_at, age_days, level 0-4, label, reused}]` |
| `get_entry(id)` | `{ok, entry:{id, website, username, password, category, favorite, updated_at}}` |
| `add_entry(data)` / `update_entry(id, data)` / `delete_entry(id)` / `set_favorite(id, bool)` | `{ok, id?}` |
| `copy_text(text, clear_after_seconds)` | `{ok}`; Python owns the clipboard and clears it only if unchanged |
| `check_strength(password)` | `{bits, level, label}` |
| `generate(options)` | `{password, bits, level, label}` |
| `check_breaches()` | `{ok, checked, failed, compromised:{entry_id: times_seen}}`. Online and opt-in: sends only 5-character SHA-1 prefixes to haveibeenpwned.com |
| `security_report()` | `{total, score, grade, levels[5], weak[ids], old[ids], reused[[ids]], old_after_days}` |
| `get_settings()` / `set_settings({autolock_minutes})` | `{ok, settings}` / `{ok}` (0, 2, 5 or 10) |

Levels: 0 Terrible, 1 Weak, 2 Fair, 3 Strong, 4 Excellent. `age_days` is `null` for entries saved without a date; those are never counted as old.
