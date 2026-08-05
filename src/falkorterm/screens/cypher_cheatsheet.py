from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Markdown, Static

from falkorterm.cheatsheet import load_cheatsheet


class CypherCheatsheetScreen(ModalScreen[None]):
    """Scrollable FalkorDB Cypher reference (read-only)."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="cypher-cheatsheet-dialog"):
            yield Static("Cypher cheatsheet (FalkorDB)", id="cypher-cheatsheet-title")
            with VerticalScroll(id="cypher-cheatsheet-body"):
                yield Markdown(load_cheatsheet(), id="cypher-cheatsheet-markdown")
            with Horizontal(id="cypher-cheatsheet-actions"):
                yield Button("Close", id="btn-close-cheatsheet", variant="primary")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-cheatsheet":
            self.dismiss(None)