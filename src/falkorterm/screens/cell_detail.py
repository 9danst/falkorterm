from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from falkorterm.client.models import CellValue


class CellDetailScreen(ModalScreen[None]):
    """Show structured detail for a result cell."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("c", "copy", "Copy", show=True),
    ]

    def __init__(self, cell: CellValue, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cell = cell

    def compose(self) -> ComposeResult:
        body = self._format_body()
        with Vertical(id="cell-detail-dialog"):
            yield Static("Cell detail", id="cell-detail-title")
            yield Static(self._cell.display, id="cell-detail-display")
            yield Static(body, id="cell-detail-body")
            with Horizontal(id="cell-detail-actions"):
                yield Button("Copy", id="btn-copy-detail", variant="success")
                yield Button("Close", id="btn-close-detail", variant="primary")

    def copy_text(self) -> str:
        if self._cell.detail is not None:
            try:
                return json.dumps(self._cell.detail, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(self._cell.detail)
        return self._cell.display

    def _format_body(self) -> str:
        if self._cell.detail is None:
            return "(no structured detail)"
        try:
            return json.dumps(self._cell.detail, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(self._cell.detail)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.app.copy_to_clipboard(self.copy_text())
        self.notify("Copied to clipboard")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-detail":
            self.dismiss(None)
        elif event.button.id == "btn-copy-detail":
            self.action_copy()
