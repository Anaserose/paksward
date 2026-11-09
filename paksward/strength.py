"""Password strength estimate.

A rule-of-thumb estimator, not a guarantee. It models how a guessing attacker works: words, names, years,
common passwords and simple tricks (capital first letter, digits at the end, 0 for o) are cheap to guess;
only truly random characters are expensive. The result is a rough number of bits (each bit doubles the
guesses needed) and a level from 0 (Terrible) to 4 (Excellent).

It errs on the low side: it assumes the attacker knows about 10,000 common words, far more than the
built-in list, and charges words that look pronounceable as if they were words.
"""
import math
import re
import unicodedata

from .commonwords import TOP_PASSWORDS, WORDS as _COMMON
from .wordlist import WORDS as _GENERATOR_WORDS

LABELS = ("Terrible", "Weak", "Fair", "Strong", "Excellent")

_WORD_BITS = math.log2(10_000)                       # a word from an attacker's 10,000-word dictionary
_GENERATOR_BITS = math.log2(len(_GENERATOR_WORDS))   # words picked by this app's own generator
_TOP_BITS = 10.0
_LEET = str.maketrans({"@": "a", "4": "a", "3": "e", "$": "s", "5": "s", "0": "o", "1": "l", "7": "t", "!": "i"})
_SEQ = re.compile(r"(012|123|234|345|456|567|678|789|abc|bcd|cde|qwe|wer|asd|sdf|zxc)", re.I)
_REPEAT = re.compile(r"(.)\1{2,}")
_VOWELS = set("aeiouy")

_DICT = {w: _WORD_BITS for w in _COMMON}
_DICT.update({w: _TOP_BITS for w in TOP_PASSWORDS if w.isalpha()})
_DICT.update({w: _GENERATOR_BITS for w in _GENERATOR_WORDS})
_MAXLEN = max(map(len, _DICT))


def level_for(bits: float) -> int:
    return 0 if bits < 26 else 1 if bits < 40 else 2 if bits < 60 else 3 if bits < 80 else 4


def _pool(password: str) -> int:
    pool = 0
    pool += 26 if re.search(r"[a-z]", password) else 0
    pool += 26 if re.search(r"[A-Z]", password) else 0
    pool += 10 if re.search(r"[0-9]", password) else 0
    pool += 33 if re.search(r"[^A-Za-z0-9]", password) else 0
    return pool or 1


def _case_ok(text: str) -> bool:
    """Words are written in one case or Capitalized. Random text switches case in the middle."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and (all(c.islower() for c in letters) or all(c.isupper() for c in letters)
                              or (letters[0].isupper() and all(c.islower() for c in letters[1:])))


def _pronounceable(run: str) -> bool:
    """Looks like a word even if it is not in our list: it alternates vowels and consonants like speech does."""
    r = run.lower()
    if len(r) < 6 or not r.isalpha():
        return False
    ratio = sum(c in _VOWELS for c in r) / len(r)
    return 0.28 <= ratio <= 0.6 and not re.search(r"[^aeiouy]{4}|[aeiou]{3}", r)


def _digit_bits(run: str) -> float:
    if re.fullmatch(r"(19|20)\d\d", run):
        return 7.0                                    # a year
    if len(set(run)) == 1 or run in "0123456789" or run in "9876543210":
        return 4.0                                    # 1111, 12345, 54321
    return 3.32 * len(run)


def _fold(text: str) -> str:
    """Lowercase, drop accents (one character in, one out) and undo common look-alike substitutions."""
    return "".join(unicodedata.normalize("NFKD", c)[0] for c in text.lower()).translate(_LEET)


def _plain_bits(part: str, pool_bits: float, between_words: bool) -> float:
    if part[0].isdigit():
        return _digit_bits(part)
    if part[0].isalpha():
        words = math.ceil(len(part) / 6) * _WORD_BITS if _case_ok(part) and _pronounceable(part) else float("inf")
        return min(len(part) * pool_bits, words)
    return (2.0 if between_words else 5.04) + 1.0 * (len(part) - 1)     # symbols: the first costs most, repeats little


def _other_bits(run: str, pool_bits: float, between_words: bool) -> float:
    """Cost of characters that are not part of a dictionary word."""
    total = 0.0
    for chunk in re.findall(r"[^\W_]+|[@$!_]+|[\W_]+", run):
        core = chunk.rstrip("0123456789!")
        if len(core) >= 6 and core[0].isalpha() and _case_ok(core) and _pronounceable(_fold(core)):
            # a word-like run written with look-alikes (Tr0ub4dor): about as cheap as a word, plus a little
            total += math.ceil(len(core) / 6) * _WORD_BITS + 2.0 + (1.0 if any(c.isupper() for c in core) else 0.0)
            tail = chunk[len(core):]
            for part in re.findall(r"\d+|\D+", tail):
                total += _plain_bits(part, pool_bits, False)
            continue
        for part in re.findall(r"\d+|[^\W\d_]+|[\W_]+", chunk):
            total += _plain_bits(part, pool_bits, between_words)
    return total


def _segment(norm: str, original: str, pool_bits: float):
    """Cheapest way to explain the password as dictionary words plus other characters."""
    n = len(norm)
    best = [0.0] + [math.inf] * n
    back = [None] * (n + 1)
    for i in range(1, n + 1):
        best[i], back[i] = best[i - 1] + pool_bits, ("c", i - 1)
        for length in range(3, min(_MAXLEN, i) + 1):
            word = norm[i - length:i]
            cost = _DICT.get(word)
            if cost is None:
                continue
            if length == 3:                            # short words only count as whole words, not inside random text
                before = original[i - 4] if i - 4 >= 0 else " "
                after = original[i] if i < n else " "
                if before.isalpha() or after.isalpha():
                    continue
            extra = (1.0 if any(c.isupper() for c in original[i - length:i]) else 0.0)
            extra += 2.0 if norm[i - length:i] != original[i - length:i].lower() else 0.0   # 0 for o, @ for a ...
            if best[i - length] + cost + extra < best[i]:
                best[i], back[i] = best[i - length] + cost + extra, ("w", i - length)
    return best[n], back


def check_strength(password: str) -> dict:
    if not password:
        return {"bits": 0, "level": 0, "label": LABELS[0]}
    pool_bits = math.log2(_pool(password))
    norm = _fold(password)
    _, back = _segment(norm, password, pool_bits)

    # Rebuild the segments, then price the leftover runs properly (years, sequences, separators).
    parts, i = [], len(norm)
    while i > 0:
        kind, j = back[i]
        parts.append((kind, j, i))
        i = j
    parts.reverse()
    total, k = 0.0, 0
    while k < len(parts):
        kind, start, end = parts[k]
        if kind == "w":
            word = norm[start:end]
            total += _DICT[word] + (1.0 if any(c.isupper() for c in password[start:end]) else 0.0) \
                + (2.0 if word != password[start:end].lower() else 0.0)
            k += 1
            continue
        run_start = start
        while k < len(parts) and parts[k][0] == "c":
            end = parts[k][2]
            k += 1
        prev_word = run_start > 0
        next_word = k < len(parts)
        total += _other_bits(password[run_start:end], pool_bits, prev_word and next_word)

    bits = min(total, len(password) * pool_bits)
    if len(set(password)) < len(password) / 3:
        bits *= 0.6
    if _REPEAT.search(password):
        bits -= 8
    if _SEQ.search(password):
        bits -= 10
    core = re.sub(r"^[^a-z]+|[^a-z]+$", "", norm)
    alnum = re.sub(r"[^a-z0-9]", "", password.lower())
    if core in TOP_PASSWORDS or alnum in TOP_PASSWORDS:
        bits = min(bits, 12.0)
    bits = max(0.0, bits)
    level = level_for(bits)
    return {"bits": int(math.floor(bits + 0.5)), "level": level, "label": LABELS[level]}
