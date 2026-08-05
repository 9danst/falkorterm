from __future__ import annotations

from typing import Literal

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Label, Static

from falkorterm.client.models import CellValue, QueryResult

GRAPH_HINT = "g table/graph · ↑↓ · Enter · x expand · c copy"
TabId = Literal["table", "graph"]


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
    """Results panel with table / ASCII graph toggle."""

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

    def compose(self):
        from falkorterm.widgets.graph import GraphResultView

        yield TableResultView(id="table-view")
        yield GraphResultView(id="graph-view")

    def on_mount(self) -> None:
        self._apply_mode_visibility()

    def prepare_manual_query(self) -> None:
        """Compatibility no-op (session merge removed in ASCII v1 restore)."""

    def begin_expand_merge(self, node_id: int) -> None:  # noqa: ARG002
        """Compatibility no-op; expand still runs a query that replaces the result."""

    @property
    def graph_focus_id(self) -> int | None:
        return None

    def show_result(self, result: QueryResult) -> None:
        from falkorterm.widgets.graph import GraphResultView

        self._last_result = result
        self.query_one("#table-view", TableResultView).show_result(result)
        self.query_one("#graph-view", GraphResultView).show_result(result)
        self._refresh_chrome()
        self._apply_mode_visibility()

    def show_error(self, message: str) -> None:
        from falkorterm.widgets.graph import GraphResultView

        self._last_result = None
        self.query_one("#table-view", TableResultView).show_error(message)
        self.query_one("#graph-view", GraphResultView).show_error(message)
        mode_tag = " · graph" if self._mode == "graph" else ""
        self.border_title = f"Results · error{mode_tag}"
        self.border_subtitle = ""
        self._apply_mode_visibility()

    def _refresh_chrome(self) -> None:
        result = self._last_result
        mode_tag = " · graph" if self._mode == "graph" else ""
        if result is None:
            self.border_title = f"Results{mode_tag}"
            self.border_subtitle = GRAPH_HINT if self._mode == "graph" else ""
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
        else:
            self.border_subtitle = elapsed or ""

    @property
    def last_result(self) -> QueryResult | None:
        return self._last_result

    @property
    def mode(self) -> TabId:
        return self._mode

    def action_toggle_graph(self) -> None:
        self._mode = "graph" if self._mode == "table" else "table"
        self._apply_mode_visibility()
        self._refresh_chrome()
        self.focus_active_view()

    def focus_active_view(self) -> None:
        from falkorterm.widgets.graph import GraphResultView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).focus()
        else:
            self.query_one("#results-table", DataTable).focus()

    def _apply_mode_visibility(self) -> None:
        from falkorterm.widgets.graph import GraphResultView

        table = self.query_one("#table-view", TableResultView)
        graph = self.query_one("#graph-view", GraphResultView)
        table.display = self._mode == "table"
        graph.display = self._mode == "graph"

    def action_copy_cell(self) -> None:
        from falkorterm.widgets.graph import GraphResultView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).copy_selected()
        else:
            self.query_one("#table-view", TableResultView).copy_cell()

    def action_copy_row(self) -> None:
        if self._mode == "table":
            self.query_one("#table-view", TableResultView).copy_row()

    def action_copy_graph(self) -> None:
        from textual.actions import SkipAction

        from falkorterm.widgets.graph import GraphResultView

        if self._mode == "graph":
            self.query_one("#graph-view", GraphResultView).copy_canvas()
        else:
            raise SkipAction()
