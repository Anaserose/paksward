"""System clipboard through the OS's own tools. Text goes in through stdin, so a password never
appears in a process list. Every function fails soft: callers get False/None, never an exception."""
import shutil
import subprocess
import sys
import threading

_timer = None
_lock = threading.Lock()


def _commands():
    if sys.platform == "darwin":
        return ["pbcopy"], ["pbpaste"]
    if sys.platform.startswith("win"):
        return (["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"])
    for tool, c, p in (("wl-copy", ["wl-copy"], ["wl-paste", "--no-newline"]),
                       ("xclip", ["xclip", "-selection", "clipboard"], ["xclip", "-selection", "clipboard", "-o"]),
                       ("xsel", ["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"])):
        if shutil.which(tool):
            return c, p
    return None, None


def copy(text: str) -> bool:
    cmd, _ = _commands()
    if not cmd or not shutil.which(cmd[0]):
        return False
    try:
        subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=5, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def paste():
    _, cmd = _commands()
    if not cmd or not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, check=True, timeout=5, capture_output=True).stdout.decode("utf-8", "replace")
        return out
    except (OSError, subprocess.SubprocessError):
        return None


def copy_and_schedule_clear(text: str, seconds: int, copy_fn=copy, paste_fn=paste) -> bool:
    """Copy, then after `seconds` clear the clipboard only if it still holds what we put there."""
    global _timer
    if not copy_fn(text):
        return False
    with _lock:
        if _timer:
            _timer.cancel()
        if seconds and seconds > 0:
            def clear():
                current = paste_fn()
                if current is not None and current.rstrip("\r\n") == text.rstrip("\r\n"):
                    copy_fn("")
            _timer = threading.Timer(seconds, clear)
            _timer.daemon = True
            _timer.start()
    return True
