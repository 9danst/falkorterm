from __future__ import annotations

from typing import Literal

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Label, Static

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.graph.extract import extract_graph
from falkorterm.graph.session import SurfSession

GRAPH_HINT = "g table/graph · ↑↓ · Enter · x expand · c copy"
SURF_HINT = "g table/ascii/surf · j/k · l hop · h back · Tab · x · c"
TabId = Literal["table", "graph", "surf"]


def format_elapsed_ms(elapsed_ms: float | None) -> str | None:
    if elapsed_ms is None:
        return None
    if elapsed_ms >= 1000:
        return f"{elapsed_ms / 1000:.1f}s"
    return f"{elapsed_ms:.1f}ms"


def format_result_meta(result: QueryResult) -> str:
    if result.truncated:
        parts = [f"Showing {len(result.rows)} of {result.total_rows}"]
    else:
        n = result.total_rows
        parts = [f"{n} row" if n == 1 else f"{n} rows"]
    elapsed = format_elapsed_ms(result.elapsed_ms)
    if elapsed:
        parts.append(elapsed)
    if result.truncated:
        parts.append("truncated")
    return " · ".join(parts)


class CellInspectRequested(Message):
    """User asked to inspect a result cell."""

    def __init__(self, cell: CellValue) -> None:
        super().__init__()
        self.cell = cell


class TableResultView(Vertical):
    """Renders a QueryResult as a DataTable."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cells: list[list[CellValue]] = []
        self._last_result: QueryResult | None = None

    def compose(self):
        yield Label("", id="results-meta", classes="results-meta")
        yield DataTable(id="results-table", zebra_stripes=True)
        yield Label("", id="results-error", classes="results-error")

    def show_result(self, result: QueryResult) -> None:
        table = self.query_one("#results-table", DataTable)
        error = self.query_one("#results-error", Label)
        meta = self.query_one("#results-meta", Label)
        error.update("")
        table.clear(columns=True)
        self._cells = []
        self._last_result = result
        if result.columns:
            table.add_columns(*result.columns)
        for row in result.rows:
            cell_row = list(row)
            self._cells.append(cell_row)
            table.add_row(*[c.display if c.display else "" for c in cell_row])
        meta.update(format_result_meta(result))

    def show_error(self, message: str) -> None:
        table = self.query_one("#results-table", DataTable)
        error = self.query_one("#results-error", Label)
        meta = self.query_one("#results-meta", Label)
        table.clear(columns=True)
        self._cells = []
        self._last_result = None
        meta.update("")
        error.update(message)

    def get_cell_text(self, row: int | None, column: int | None) -> str | None:
        cell = self._cell_at(row, column)
        if cell is None:
            return None
        return cell.display

    def get_row_tsv(self, row: int | None) -> str | None:
        if row is None or row < 0 or row >= len(self._cells):
            return None
        return "\t".join(c.display for c in self._cells[row])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._inspect_coordinate(event.cursor_row, event.cursor_column)

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key == "enter":
            table = self.query_one("#results-table", DataTable)
            if not table.row_count:
                return
            self._inspect_coordinate(table.cursor_row, table.cursor_column)
            event.prevent_default()
            event.stop()
            return
        if event.key == "y":
            if self.copy_cell():
                event.prevent_default()
                event.stop()
            return
        if event.key == "Y":
            if self.copy_row():
                event.prevent_default()
                event.stop()

    def copy_cell(self) -> bool:
        table = self.query_one("#results-table", DataTable)
        text = self.get_cell_text(table.cursor_row, table.cursor_column)
        if text is None:
            return False
        self.app.copy_to_clipboard(text, what="cell")
        return True

    def copy_row(self) -> bool:
        table = self.query_one("#results-table", DataTable)
        text = self.get_row_tsv(table.cursor_row)
        if text is None:
            return False
        self.app.copy_to_clipboard(text, what="row")
        return True

    def _cell_at(self, row: int | None, column: int | None) -> CellValue | None:
        if row is None or column is None:
            return None
        if row < 0 or column < 0:
            return None
        if row >= len(self._cells):
            return None
        cell_row = self._cells[row]
        if column >= len(cell_row):
            return None
        return cell_row[column]

    def _inspect_coordinate(self, row: int | None, column: int | None) -> None:
        cell = self._cell_at(row, column)
        if cell is None:
            return
        self.post_message(CellInspectRequested(cell))


class ResultsWidget(Static):
    """Results panel with table / ASCII graph / surf modes."""

    BINDINGS = [
        Binding("y", "copy_cell", "Copy cell", show=False),
        Binding("Y", "copy_row", "Copy row", show=False),
        Binding("g", "toggle_graph", "Toggle graph", show=False),
        Binding("c", "copy_graph", "Copy graph", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Results"
        self._last_result: QueryResult | None = None
        self._mode: TabId = "table"
        self._surf = SurfSession()
        self._pending_expand_merge = False
        self._pending_expand_node_id: int | None = None

    def compose(self):
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        yield TableResultView(id="table-view")
        yield GraphResultView(id="graph-view")
        yield SurfView(id="surf-view")

    def on_mount(self) -> None:
        self._apply_mode_visibility()

    def prepare_manual_query(self) -> None:
        """Mark the next result as a fresh manual query for Surf."""
        self._pending_expand_merge = False
        self._pending_expand_node_id = None

    def begin_expand_merge(self, node_id: int) -> None:
        """Mark the next result as an expansion to merge into Surf."""
        self._pending_expand_merge = True
        self._pending_expand_node_id = node_id

    @property
    def graph_focus_id(self) -> int | None:
        return self._surf.focus_id

    def show_result(self, result: QueryResult) -> None:
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        self._last_result = result
        self.query_one("#table-view", TableResultView).show_result(result)
        self.query_one("#graph-view", GraphResultView).show_result(result)
        incoming = extract_graph(result)
        if self._pending_expand_merge:
            self._surf.merge(incoming)
            self._restore_expand_focus()
            self._pending_expand_merge = False
            self._pending_expand_node_id = None
        else:
            self._surf.seed(incoming)
        self.query_one("#surf-view", SurfView).set_session(self._surf)
        self._refresh_chrome()
        self._apply_mode_visibility()

    def show_error(self, message: str) -> None:
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        self._last_result = None
        self._pending_expand_merge = False
        self._pending_expand_node_id = None
        self._surf.clear()
        self.query_one("#table-view", TableResultView).show_error(message)
        self.query_one("#graph-view", GraphResultView).show_error(message)
        self.query_one("#surf-view", SurfView).show_error(message)
        mode_tag = self._mode_tag()
        self.border_title = f"Results · error{mode_tag}"
        self.border_subtitle = ""
        self._apply_mode_visibility()

    def _refresh_chrome(self) -> None:
        result = self._last_result
        mode_tag = self._mode_tag()
        if result is None:
            self.border_title = f"Results{mode_tag}"
            self.border_subtitle = self._active_hint()
            return
        n = result.total_rows
        shown = len(result.rows)
        if result.truncated:
            self.border_title = f"Results · {shown}/{n}{mode_tag}"
        else:
            self.border_title = f"Results · {n}{mode_tag}"
        elapsed = format_elapsed_ms(result.elapsed_ms)
        if self._mode == "graph":
            self.border_subtitle = (
                f"{elapsed} · {GRAPH_HINT}" if elapsed else GRAPH_HINT
            )
        elif self._mode == "surf":
            self.border_subtitle = (
                f"{elapsed} · {SURF_HINT}" if elapsed else SURF_HINT
            )
        else:
            self.border_subtitle = elapsed or ""

    def _mode_tag(self) -> str:
        if self._mode == "graph":
            return " · graph"
        if self._mode == "surf":
            return " · surf"
        return ""

    def _active_hint(self) -> str:
        if self._mode == "graph":
            return GRAPH_HINT
        if self._mode == "surf":
            return SURF_HINT
        return ""

    @property
    def last_result(self) -> QueryResult | None:
        return self._last_result

    @property
    def mode(self) -> TabId:
        return self._mode

    def action_toggle_graph(self) -> None:
        order: tuple[TabId, ...] = ("table", "graph", "surf")
        self._mode = order[(order.index(self._mode) + 1) % len(order)]
        self._apply_mode_visibility()
        self._refresh_chrome()
        self.focus_active_view()

    def focus_active_view(self) -> None:
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).focus()
        elif self._mode == "surf":
            self.query_one("#surf-view", SurfView).focus()
        else:
            self.query_one("#results-table", DataTable).focus()

    def _apply_mode_visibility(self) -> None:
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        table = self.query_one("#table-view", TableResultView)
        graph = self.query_one("#graph-view", GraphResultView)
        surf = self.query_one("#surf-view", SurfView)
        table.display = self._mode == "table"
        graph.display = self._mode == "graph"
        surf.display = self._mode == "surf"

    def _restore_expand_focus(self) -> None:
        node_id = self._pending_expand_node_id
        if self._surf.model is None or node_id is None:
            return
        if any(node.id == node_id for node in self._surf.model.nodes):
            self._surf.focus_id = node_id
            self._surf.neighbor_index = -1
            self._surf.select_kind = "node"

    def action_copy_cell(self) -> None:
        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).copy_selected()
        elif self._mode == "surf":
            self.query_one("#surf-view", SurfView).copy_selection()
        else:
            self.query_one("#table-view", TableResultView).copy_cell()

    def action_copy_row(self) -> None:
        from falkorterm.widgets.surf import SurfView

        if self._mode == "table":
            self.query_one("#table-view", TableResultView).copy_row()
        elif self._mode == "surf":
            self.query_one("#surf-view", SurfView).copy_selection()

    def action_copy_graph(self) -> None:
        from textual.actions import SkipAction

        from falkorterm.widgets.graph import GraphResultView
        from falkorterm.widgets.surf import SurfView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).copy_canvas()
        elif self._mode == "surf":
            self.query_one("#surf-view", SurfView).copy_canvas()
        else:
            raise SkipAction()
