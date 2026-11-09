"""Password generation."""
import math as _math
import random
import secrets
import string

from .strength import LABELS as _LABELS, level_for as _level_for
from .wordlist import WORDS as _WORDS

_LOWER = string.ascii_lowercase
_UPPER = string.ascii_uppercase
_DIGITS = string.digits
_SYMBOLS = "!@#$%^&*()-_=+?"
_AMBIGUOUS = set("Il1O0o")


def _result(password: str, bits: float) -> dict:
    level = _level_for(bits)
    return {"password": password, "bits": int(_math.floor(bits + 0.5)), "level": level, "label": _LABELS[level]}


def generate(options=None) -> dict:
    """Generate a password or passphrase. Uses `secrets` only. Out-of-range values are clamped."""
    o = options or {}
    if o.get("mode") == "passphrase":
        n = min(10, max(3, int(o.get("words") or 7)))
        sep = o.get("separator")
        sep = "-" if sep is None else str(sep)[:3]
        words = [secrets.choice(_WORDS) for _ in range(n)]
        if o.get("capitalize"):
            words = [w.capitalize() for w in words]
        pw = sep.join(words)
        bits = n * _math.log2(len(_WORDS))
        if o.get("digits"):
            pw += sep + str(secrets.randbelow(100))
            bits += _math.log2(100)
        return _result(pw, bits)

    length = min(64, max(8, int(o.get("length") or 16)))
    sets = []
    if o.get("lower", True):
        sets.append(_LOWER)
    if o.get("upper", True):
        sets.append(_UPPER)
    if o.get("digits", True):
        sets.append(_DIGITS)
    if o.get("symbols", True):
        sets.append(_SYMBOLS)
    if not sets:
        sets.append(_LOWER)
    if o.get("avoidAmbiguous"):
        sets = ["".join(c for c in s if c not in _AMBIGUOUS) for s in sets]
    pool = "".join(sets)
    chars = [secrets.choice(s) for s in sets]            # at least one of every enabled class
    chars += [secrets.choice(pool) for _ in range(length - len(chars))]
    random.SystemRandom().shuffle(chars)
    return _result("".join(chars), length * _math.log2(len(pool)))
