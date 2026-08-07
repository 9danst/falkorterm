from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, TabbedContent, TabPane, Tree

from falkorterm.client.models import CellValue
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.screens.cell_detail_format import (
    add_json_to_tree,
    format_header_text,
    iter_property_rows,
)

_TAB_PROPERTIES = "tab-properties"
_TAB_JSON = "tab-json"


def _node_id(cell: CellValue) -> int | None:
    detail = cell.detail
    if not detail or detail.get("kind") != "node":
        return None
    node_id = detail.get("id")
    if isinstance(node_id, bool) or not isinstance(node_id, int):
        return None
    return node_id


class CellDetailScreen(ModalScreen[None]):
    """Show structured detail for a result cell."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
        Binding("c", "copy", "Copy", show=True),
        Binding("x", "expand", "Expand", show=False),
        Binding("tab", "toggle_tab", "Toggle tab", show=True, priority=True),
        Binding("t", "toggle_tab", "Toggle tab", show=False),
    ]

    def __init__(self, cell: CellValue, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cell = cell
        self._expand_id = _node_id(cell)

    def compose(self) -> ComposeResult:
        with Vertical(id="cell-detail-dialog"):
            yield Static("Cell detail", id="cell-detail-title")
            yield Static(format_header_text(self._cell), id="cell-detail-header")
            yield Static(self._cell.display, id="cell-detail-display")
            with TabbedContent(id="cell-detail-tabs", initial=_TAB_PROPERTIES):
                with TabPane("Properties", id=_TAB_PROPERTIES):
                    with VerticalScroll(id="cell-detail-props-scroll"):
                        yield DataTable(
                            id="cell-detail-props",
                            zebra_stripes=True,
                            cursor_type="cell",
                            cell_padding=2,
                        )
                with TabPane("JSON", id=_TAB_JSON):
                    with VerticalScroll(id="cell-detail-json-scroll"):
                        yield Tree("detail", id="cell-detail-tree")
            with Horizontal(id="cell-detail-actions"):
                if self._expand_id is not None:
                    yield Button(
                        "Expand", id="btn-expand-neighbors", variant="warning"
                    )
                yield Button("Copy", id="btn-copy-detail", variant="success")
                yield Button("Close", id="btn-close-detail", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one("#cell-detail-props", DataTable)
        table.add_columns("Key", "Value")
        for key, value in iter_property_rows(self._cell):
            table.add_row(key, value)

        tree = self.query_one("#cell-detail-tree", Tree)
        data = (
            self._cell.detail
            if self._cell.detail is not None
            else {"display": self._cell.display}
        )
        add_json_to_tree(tree, data)

    def full_detail_text(self) -> str:
        if self._cell.detail is not None:
            try:
                return json.dumps(self._cell.detail, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(self._cell.detail)
        return self._cell.display

    def copy_text(self) -> str:
        """Text for copy: selected cell/tree value if available, else full detail."""
        selected = self._selected_value_text()
        if selected is not None:
            return selected
        return self.full_detail_text()

    def _selected_value_text(self) -> str | None:
        focused = self.focused
        if isinstance(focused, DataTable) and focused.id == "cell-detail-props":
            if focused.row_count == 0:
                return None
            try:
                value = focused.get_cell_at(focused.cursor_coordinate)
            except Exception:
                return None
            return str(value)

        if isinstance(focused, Tree) and focused.id == "cell-detail-tree":
            node = focused.cursor_node
            if node is None:
                return None
            return str(node.label)

        return None

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        selected = self._selected_value_text()
        if selected is not None:
            self.app.copy_to_clipboard(selected, what="value")
        else:
            self.app.copy_to_clipboard(self.full_detail_text(), what="detail")

    def action_toggle_tab(self) -> None:
        tabs = self.query_one("#cell-detail-tabs", TabbedContent)
        if tabs.active == _TAB_JSON:
            tabs.active = _TAB_PROPERTIES
            self.query_one("#cell-detail-props", DataTable).focus()
        else:
            tabs.active = _TAB_JSON
            self.query_one("#cell-detail-tree", Tree).focus()

    def action_expand(self) -> None:
        if self._expand_id is None:
            return
        self.post_message(ExpandNeighborsRequested(self._expand_id))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-detail":
            self.dismiss(None)
        elif event.button.id == "btn-copy-detail":
            self.app.copy_to_clipboard(self.full_detail_text(), what="detail")
        elif event.button.id == "btn-expand-neighbors":
            self.action_expand()
