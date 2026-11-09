"""Paths and constants. Paths are module attributes so tests can redirect them."""
import os
import sys

FROZEN = bool(getattr(sys, "frozen", False))          # True inside a packaged (PyInstaller) app

# Project root when run from source; the unpacked bundle folder when packaged.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
FRONTEND_DIR = os.path.join(RESOURCE_DIR, "frontend")


def _user_dir() -> str:
    """Per-user application folder for this operating system."""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, "Paksward")


# The encrypted vault and account list. Source runs keep them next to main.py;
# a packaged app cannot write inside itself, so it uses the per-user folder.
DATA_DIR = os.environ.get("PAKSWARD_DATA_DIR") or (
    os.path.join(_user_dir(), "vault") if FROZEN else os.path.join(APP_DIR, "data"))
VAULTS_DIR = os.path.join(DATA_DIR, "vaults")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# The Secret Key for this device. Deliberately NOT inside DATA_DIR: copying, syncing or emailing
# the data folder must not also hand over the key that makes its contents unguessable.
SECRET_DIR = os.environ.get("PAKSWARD_SECRET_DIR") or os.path.join(_user_dir(), "device")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_HOURS = 24
CLIPBOARD_CLEAR_MS = 30_000
AUTOLOCK_CHOICES = (0, 2, 5, 10)        # minutes; 0 = never
DEFAULT_AUTOLOCK_MINUTES = 5
OLD_AFTER_DAYS = 180
MIN_PASSWORD_LENGTH = 10
