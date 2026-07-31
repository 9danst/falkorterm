from __future__ import annotations

import re
from dataclasses import dataclass

from textual.widgets import TextArea

_WORD_RE = re.compile(r"[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class SchemaTokens:
    labels: tuple[str, ...] = ()
    relations: tuple[str, ...] = ()
    properties: tuple[str, ...] = ()

    @property
    def all_tokens(self) -> tuple[str, ...]:
        seen: list[str] = []
        for name in (*self.labels, *self.relations, *self.properties):
            if name not in seen:
                seen.append(name)
        return tuple(seen)


def _prefix_at(text: str, cursor: int) -> tuple[str, str]:
    """Return (before_prefix, prefix) ending at cursor."""
    before = text[:cursor]
    match = _WORD_RE.search(before)
    if not match:
        return before, ""
    return before[: match.start()], match.group(0)


def _context_tokens(before_prefix: str, tokens: SchemaTokens) -> tuple[str, ...]:
    stripped = before_prefix.rstrip()
    if re.search(r"\[[\w]*:$", stripped):
        return tokens.relations or tokens.all_tokens
    if stripped.endswith("."):
        return tokens.properties or tokens.all_tokens
    if stripped.endswith(":"):
        return tokens.labels or tokens.all_tokens
    return tokens.all_tokens


def suggest_completion(
    text: str,
    cursor: int,
    tokens: SchemaTokens,
) -> str:
    """Return the suffix to append as ghost suggestion (not including the prefix)."""
    before_prefix, prefix = _prefix_at(text, cursor)
    if not prefix:
        return ""
    candidates = _context_tokens(before_prefix, tokens)
    if not candidates:
        return ""
    lower = prefix.lower()
    matches = [
        t for t in candidates if t.lower().startswith(lower) and t.lower() != lower
    ]
    if not matches:
        return ""
    preferred = next((t for t in matches if t.startswith(prefix)), matches[0])
    return preferred[len(prefix) :]


class CypherTextArea(TextArea):
    """TextArea with schema-aware ghost suggestions."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._schema_tokens = SchemaTokens()

    def set_schema_tokens(self, tokens: SchemaTokens) -> None:
        self._schema_tokens = tokens
        self.update_suggestion()

    def update_suggestion(self) -> None:
        try:
            row, col = self.cursor_location
            lines = self.text.split("\n")
            offset = sum(len(lines[i]) + 1 for i in range(row)) + col
            offset = min(max(offset, 0), len(self.text))
            self.suggestion = suggest_completion(
                self.text, offset, self._schema_tokens
            )
        except Exception:  # noqa: BLE001
            self.suggestion = ""
