"""System clipboard helpers (OSC 52 is unreliable in many terminals)."""

from __future__ import annotations

import shutil
import subprocess

CLIPBOARD_MISSING_HINT = "install wl-clipboard (Wayland) or xclip (X11)"


def format_copy_notification(ok: bool, what: str) -> tuple[str, str]:
    """Return (message, severity) for a copy attempt."""
    if ok:
        return f"Copied {what}", "information"
    return f"Could not copy {what} — {CLIPBOARD_MISSING_HINT}", "warning"


def copy_text_system(text: str) -> bool:
    """Copy via wl-copy / xclip / xsel / pbcopy when available. Returns True on success."""
    candidates: tuple[list[str], ...] = (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
    )
    payload = text.encode("utf-8")
    for cmd in candidates:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.run(
                cmd,
                input=payload,
                check=True,
                timeout=2,
                capture_output=True,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False
