"""Random keys people can write down: the Secret Key (PWSK) and the Recovery Key (PWRK).

Each holds 160 random bits, shown as 8 groups of 4 letters/digits plus a 4-character checksum, so a
typo is reported as a typo instead of as a wrong key. These are not passwords a person chooses: they
are generated here, which is what makes them impossible to guess.
"""
import base64
import hashlib
import hmac
import re
import secrets

SECRET_PREFIX = "PWSK"
RECOVERY_PREFIX = "PWRK"
KEY_BYTES = 20                       # 160 bits -> exactly 32 base32 characters


class KeyFormatError(ValueError):
    """The text is not a well-formed key (wrong prefix, length or checksum)."""


def generate() -> bytes:
    return secrets.token_bytes(KEY_BYTES)


def _checksum(prefix: str, raw: bytes) -> str:
    return base64.b32encode(hashlib.sha256(prefix.encode() + raw).digest()[:3]).decode()[:4]


def format_key(prefix: str, raw: bytes) -> str:
    body = base64.b32encode(raw).decode()
    groups = [body[i:i + 4] for i in range(0, len(body), 4)] + [_checksum(prefix, raw)]
    return "-".join([prefix] + groups)


def parse_key(prefix: str, text: str) -> bytes:
    cleaned = re.sub(r"[^A-Z0-9]", "", (text or "").upper())
    if not cleaned.startswith(prefix):
        raise KeyFormatError("wrong kind of key")
    body = cleaned[len(prefix):]
    if len(body) != 36:
        raise KeyFormatError("wrong length")
    try:
        raw = base64.b32decode(body[:32])
    except ValueError:
        raise KeyFormatError("bad characters") from None
    if not hmac.compare_digest(_checksum(prefix, raw), body[32:]):
        raise KeyFormatError("checksum mismatch")
    return raw
