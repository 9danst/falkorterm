from __future__ import annotations

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static

from falkorterm.history import HistoryStore
from falkorterm.widgets.cypher_area import CypherTextArea, SchemaTokens


class QuerySubmitted(Message):
    """Emitted when the user submits a Cypher query."""

    def __init__(self, cypher: str) -> None:
        super().__init__()
        self.cypher = cypher


class QueryWidget(Static):
    """Cypher editor with in-memory (+ optional persistent) history."""

    BINDINGS = [
        Binding("ctrl+shift+c", "copy_query", "Copy query", show=False),
    ]

    _HINT = "Ctrl+Enter · ↑↓ history"
    _HINT_RUNNING = "Esc cancel (disconnects query)"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Cypher query"
        self.border_subtitle = self._HINT
        self._history: list[str] = []
        self._history_index: int | None = None
        self._history_store: HistoryStore | None = None
        self._history_target: str = ""

    def compose(self):
        yield CypherTextArea(id="cypher-input")

    def action_copy_query(self) -> None:
        text = self.get_text()
        if not text:
            return
        self.app.copy_to_clipboard(text)
        self.notify("Copied query")

    def on_mount(self) -> None:
        # Prefer SQL highlighting as a stand-in; Cypher is not a built-in language.
        area = self.query_one("#cypher-input", CypherTextArea)
        try:
            area.language = "sql"
        except Exception:  # noqa: BLE001
            pass

    def configure_history(self, store: HistoryStore, target: str) -> None:
        self._history_store = store
        self._history_target = target
        self.set_history(store.load(target))

    def set_schema_tokens(
        self,
        labels: tuple[str, ...] | list[str] = (),
        relations: tuple[str, ...] | list[str] = (),
        properties: tuple[str, ...] | list[str] = (),
    ) -> None:
        tokens = SchemaTokens(
            labels=tuple(labels),
            relations=tuple(relations),
            properties=tuple(properties),
        )
        self.query_one("#cypher-input", CypherTextArea).set_schema_tokens(tokens)

    def set_history(self, entries: list[str]) -> None:
        self._history = list(entries)
        self._history_index = None

    def get_text(self) -> str:
        return self.query_one("#cypher-input", CypherTextArea).text

    def set_text(self, text: str) -> None:
        area = self.query_one("#cypher-input", CypherTextArea)
        area.load_text(text)

    def insert_template(self, text: str) -> None:
        self.set_text(text)
        self.query_one("#cypher-input", CypherTextArea).focus()

    def append_snippet(self, snippet: str) -> None:
        current = self.get_text()
        if current.strip():
            self.set_text(current.rstrip() + " " + snippet)
        else:
            self.set_text(snippet)
        self.query_one("#cypher-input", CypherTextArea).focus()

    def set_running(self, running: bool) -> None:
        if running:
            self.border_title = "Cypher query · Running…"
            self.border_subtitle = self._HINT_RUNNING
            self.add_class("running")
        else:
            self.border_title = "Cypher query"
            self.border_subtitle = self._HINT
            self.remove_class("running")

    def submit(self) -> None:
        cypher = self.get_text().strip()
        if not cypher:
            return
        if not self._history or self._history[-1] != cypher:
            self._history.append(cypher)
        self._history_index = None
        if self._history_store is not None and self._history_target:
            self._history_store.append(self._history_target, cypher)
        self.post_message(QuerySubmitted(cypher))

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key not in ("up", "down"):
            return
        area = self.query_one("#cypher-input", CypherTextArea)
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
