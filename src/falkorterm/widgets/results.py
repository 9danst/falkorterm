from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Label, Static

from falkorterm.client.models import CellValue, QueryResult


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
        self.app.copy_to_clipboard(text)
        self.notify("Copied cell")
        return True

    def copy_row(self) -> bool:
        table = self.query_one("#results-table", DataTable)
        text = self.get_row_tsv(table.cursor_row)
        if text is None:
            return False
        self.app.copy_to_clipboard(text)
        self.notify("Copied row")
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
    """Results panel with table view and row/timing meta."""

    BINDINGS = [
        Binding("y", "copy_cell", "Copy cell", show=False),
        Binding("Y", "copy_row", "Copy row", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Results"
        self._last_result: QueryResult | None = None

    def compose(self):
        yield TableResultView(id="table-view")

    def show_result(self, result: QueryResult) -> None:
        self._last_result = result
        self.query_one("#table-view", TableResultView).show_result(result)
        n = result.total_rows
        shown = len(result.rows)
        if result.truncated:
            self.border_title = f"Results · {shown}/{n}"
        else:
            self.border_title = f"Results · {n}"
        elapsed = format_elapsed_ms(result.elapsed_ms)
        self.border_subtitle = elapsed or ""

    def show_error(self, message: str) -> None:
        self._last_result = None
        self.query_one("#table-view", TableResultView).show_error(message)
        self.border_title = "Results · error"
        self.border_subtitle = ""

    @property
    def last_result(self) -> QueryResult | None:
        return self._last_result

    def action_copy_cell(self) -> None:
        self.query_one("#table-view", TableResultView).copy_cell()

    def action_copy_row(self) -> None:
        self.query_one("#table-view", TableResultView).copy_row()
