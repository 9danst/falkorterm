from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from falkorterm.export import ExportFormat


class ExportFormatScreen(ModalScreen[ExportFormat | None]):
    """Choose CSV or JSON export format."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="export-format-dialog"):
            yield Static("Export results", id="export-format-title")
            yield Static("Choose a format:")
            with Horizontal(id="export-format-actions"):
                yield Button("CSV", id="btn-export-csv", variant="primary")
                yield Button("JSON", id="btn-export-json", variant="success")
                yield Button("Cancel", id="btn-export-cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-export-csv":
            self.dismiss("csv")
        elif event.button.id == "btn-export-json":
            self.dismiss("json")
        elif event.button.id == "btn-export-cancel":
            self.dismiss(None)
