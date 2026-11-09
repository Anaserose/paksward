"""Password-health analysis. Works on in-memory entries and never sends passwords anywhere."""
from .config import OLD_AFTER_DAYS
from .entries import age_days
from .strength import check_strength


def reuse_groups(entries: list) -> list:
    """Lists of entry ids that share an identical password (groups of two or more)."""
    by = {}
    for e in entries:
        by.setdefault(e["password"], []).append(e["id"])
    return [ids for ids in by.values() if len(ids) > 1]


def reuse_counts(entries: list) -> dict:
    return {i: len(g) for g in reuse_groups(entries) for i in g}


def entry_meta(entry: dict, reused: int = 1, now=None) -> dict:
    """What the list view may see about an entry. Contains no password."""
    s = check_strength(entry["password"])
    age = age_days(entry, now)
    return {
        "id": entry["id"], "website": entry["website"], "username": entry["username"],
        "category": entry["category"], "favorite": entry["favorite"],
        "updated_at": entry.get("updated_at"), "age_days": None if age is None else round(age),
        "level": s["level"], "label": s["label"], "reused": reused,
    }


def security_report(entries: list, now=None) -> dict:
    reuse = reuse_counts(entries)
    levels = [0] * 5
    weak, old, loss = [], [], 0
    for e in entries:
        s = check_strength(e["password"])
        levels[s["level"]] += 1
        penalty = 0
        if s["level"] <= 1:
            weak.append(e["id"])
            penalty += 40
        elif s["level"] == 2:
            penalty += 15                  # Fair: not flagged as weak, but not full marks either
        if e["id"] in reuse:
            penalty += 35
        age = age_days(e, now)
        if age is not None and age > OLD_AFTER_DAYS:
            old.append(e["id"])
            penalty += 15
        loss += min(100, penalty)
    n = len(entries)
    score = round(100 - loss / n) if n else 100
    grade = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "At risk"
    return {"total": n, "score": score, "grade": grade, "levels": levels, "weak": weak, "old": old,
            "reused": reuse_groups(entries), "old_after_days": OLD_AFTER_DAYS}
