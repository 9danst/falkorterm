from __future__ import annotations

EMPTY_MESSAGE = "No graph data in this result"

_LABEL_PALETTE: tuple[str, ...] = (
    "cyan",
    "magenta",
    "yellow",
    "green",
    "blue",
    "red",
    "bright_cyan",
    "bright_magenta",
    "bright_yellow",
    "bright_green",
    "bright_blue",
    "bright_red",
)


def color_for(name: str) -> str:
    """Return a stable Rich style name for a label or relationship type."""
    # Avoid built-in hash(): PYTHONHASHSEED randomizes str hashes per process.
    digest = 0
    for ch in name:
        digest = (digest * 131 + ord(ch)) & 0xFFFFFFFF
    return _LABEL_PALETTE[digest % len(_LABEL_PALETTE)]
