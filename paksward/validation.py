"""Input validation helpers."""
import re

from .config import MIN_PASSWORD_LENGTH
from .strength import check_strength

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match(email or ""))


def password_problem(password: str):
    """Why a new master password is not acceptable, or None if it is fine."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if check_strength(password)["level"] < 2:
        return "That password is too easy to guess. Use more words, or a longer mix of characters."
    return None
