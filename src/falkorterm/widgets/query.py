from __future__ import annotations

from textual.message import Message
from textual.widgets import Static, TextArea


class QuerySubmitted(Message):
    """Emitted when the user submits a Cypher query."""

    def __init__(self, cypher: str) -> None:
        super().__init__()
        self.cypher = cypher


class QueryWidget(Static):
    """Cypher editor with in-memory history."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Cypher query"
        self._history: list[str] = []
        self._history_index: int | None = None

    def compose(self):
        yield TextArea(id="cypher-input")

    def on_mount(self) -> None:
        # Prefer SQL highlighting as a stand-in; Cypher is not a built-in language.
        area = self.query_one("#cypher-input", TextArea)
        try:
            area.language = "sql"
        except Exception:  # noqa: BLE001
            pass

    def get_text(self) -> str:
        return self.query_one("#cypher-input", TextArea).text

    def set_text(self, text: str) -> None:
        area = self.query_one("#cypher-input", TextArea)
        area.load_text(text)

    def insert_template(self, text: str) -> None:
        self.set_text(text)
        self.query_one("#cypher-input", TextArea).focus()

    def submit(self) -> None:
        cypher = self.get_text().strip()
        if not cypher:
            return
        if not self._history or self._history[-1] != cypher:
            self._history.append(cypher)
        self._history_index = None
        self.post_message(QuerySubmitted(cypher))

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key not in ("up", "down"):
            return
        area = self.query_one("#cypher-input", TextArea)
        # Only navigate history when cursor is at the start of the document.
        if area.cursor_location != (0, 0):
            return
        if not self._history:
            return
        if event.key == "up":
            if self._history_index is None:
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            self.set_text(self._history[self._history_index])
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            if self._history_index is None:
                return
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self.set_text(self._history[self._history_index])
            else:
                self._history_index = None
                self.set_text("")
            event.prevent_default()
            event.stop()
