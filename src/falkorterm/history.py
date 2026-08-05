from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_MAX_ENTRIES = 200


def default_history_path() -> Path:
    override = os.environ.get("FALKOR_HISTORY_PATH")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "falkorterm" / "history.json"
    return Path.home() / ".local" / "share" / "falkorterm" / "history.json"


class HistoryStore:
    """Persistent Cypher history keyed by connection display_target."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self.path = path or default_history_path()
        self.max_entries = max_entries

    def load(self, target: str) -> list[str]:
        data = self._read()
        entries = data.get("entries", {})
        raw = entries.get(target, [])
        return [str(item) for item in raw]

    def append(self, target: str, cypher: str) -> None:
        text = cypher.strip()
        if not text:
            return
        data = self._read()
        entries: dict[str, list[str]] = {
            str(k): [str(x) for x in v]
            for k, v in data.get("entries", {}).items()
        }
        history = list(entries.get(target, []))
        if history and history[-1] == text:
            return
        history.append(text)
        if len(history) > self.max_entries:
            history = history[-self.max_entries :]
        entries[target] = history
        self._write({"entries": entries})

    def _read(self) -> dict:
        if not self.path.exists():
            return {"entries": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"entries": {}}
        if not isinstance(raw, dict):
            return {"entries": {}}
        return raw

    def _write(self, data: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError:
            # Best-effort persistence; ignore unwritable paths (sandbox, etc.).
            return
