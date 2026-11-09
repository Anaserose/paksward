"""Optional online check: has a password appeared in a known data breach?

This is the only place the app uses the internet, and only when the person presses "Check now".
It uses the Have I Been Pwned range API with k-anonymity: for each password we compute its SHA-1
fingerprint and send ONLY the first 5 characters of it. The service answers with every fingerprint
ending that starts with those 5 characters (hundreds of them), and the comparison happens here.
The password and the remaining 35 characters never leave this computer.
"""
import hashlib
import re
import time
import urllib.error
import urllib.request

URL = "https://api.pwnedpasswords.com/range/"
MAX_RESPONSE = 2_000_000
_PREFIX = re.compile(r"[0-9A-F]{5}")


class BreachCheckError(Exception):
    """The breach service could not be reached or gave an unusable answer."""


def split_hash(password: str):
    """(first 5 characters, remaining 35) of the SHA-1 fingerprint, upper case."""
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    return digest[:5], digest[5:]


def fetch_range(prefix: str, timeout: float = 8.0) -> str:
    """Ask the service for everything that starts with this 5-character prefix. Nothing else is sent."""
    if not _PREFIX.fullmatch(prefix):
        raise ValueError("prefix must be 5 hex characters")
    request = urllib.request.Request(URL + prefix, headers={"Add-Padding": "true", "User-Agent": "Paksward-breach-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:      # HTTPS, certificate checked
            if not response.geturl().startswith(URL):
                raise BreachCheckError("unexpected redirect")
            body = response.read(MAX_RESPONSE + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise BreachCheckError(type(exc).__name__) from None
    if len(body) > MAX_RESPONSE:
        raise BreachCheckError("answer too large")
    return body.decode("ascii", "replace")


def parse_range(text: str) -> dict:
    """{fingerprint ending: times seen}. Padding lines (count 0) and junk are ignored."""
    seen = {}
    for line in text.splitlines():
        suffix, _, count = line.strip().partition(":")
        if len(suffix) == 35 and count.strip().isdigit() and int(count) > 0:
            seen[suffix.upper()] = int(count)
    return seen


def check(passwords, fetch=fetch_range, budget_seconds: float = 45.0, cancelled =lambda: False):
    """For each distinct password, how many times it appears in known breaches (0 if not found).

    Returns (counts, failed): counts maps password -> times seen for every password that could be
    checked; failed is how many distinct passwords could not be checked (network trouble or out of time).
    One request is made per distinct 5-character prefix.
    """
    deadline = time.monotonic() + budget_seconds
    groups = {}
    for pw in set(passwords):
        prefix, suffix = split_hash(pw)
        groups.setdefault(prefix, []).append((pw, suffix))
    counts, failed = {}, 0
    for prefix, members in groups.items():
        try:
            if time.monotonic() > deadline or cancelled():
                raise BreachCheckError("out of time or cancelled")
            seen = parse_range(fetch(prefix))
        except (BreachCheckError, OSError):
            failed += len(members)
            continue
        for pw, suffix in members:
            counts[pw] = seen.get(suffix, 0)
    return counts, failed
