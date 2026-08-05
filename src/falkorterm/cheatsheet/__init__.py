"""Packaged Cypher reference content for FalkorDB."""

from __future__ import annotations

from pathlib import Path

_CHEATSHEET_PATH = Path(__file__).with_name("cypher_falkordb.md")


def load_cheatsheet() -> str:
    """Return the FalkorDB Cypher cheatsheet markdown."""
    return _CHEATSHEET_PATH.read_text(encoding="utf-8")
