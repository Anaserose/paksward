"""Vault entry model. Older vaults store only {website, username, password}; newer ones add optional fields.

Old vaults open unchanged: missing fields get defaults in memory and are written back only when
the user next saves something. A missing `updated_at` means "unknown", never "old".
"""
import secrets
from datetime import datetime, timezone

CATEGORIES = ("Work", "Email", "Banking", "Shopping", "Social", "Entertainment", "Other")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return secrets.token_hex(6)


def normalize(entries: list) -> bool:
    """Fill in missing fields in place. Returns True if anything changed."""
    changed = False
    seen = set()
    for e in entries:
        if not e.get("id") or e["id"] in seen:
            e["id"] = new_id()
            changed = True
        seen.add(e["id"])
        if e.get("category") not in CATEGORIES:
            e["category"] = "Other"
            changed = True
        if not isinstance(e.get("favorite"), bool):
            e["favorite"] = False
            changed = True
    return changed


def age_days(entry: dict, now=None):
    """Days since the password last changed, or None if unknown."""
    stamp = entry.get("updated_at")
    if not stamp:
        return None
    try:
        then = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return max(0.0, ((now or datetime.now(timezone.utc)) - then).total_seconds() / 86400)
