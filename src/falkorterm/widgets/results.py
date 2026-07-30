from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import DataTable, Label, Static

from falkorterm.client.models import QueryResult


class TableResultView(Vertical):
    """Renders a QueryResult as a DataTable."""

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
        if result.columns:
            table.add_columns(*result.columns)
        for row in result.rows:
            table.add_row(*["" if c is None else str(c) for c in row])
        if result.truncated:
            meta.update(f"Showing {len(result.rows)} of {result.total_rows}")
        else:
            meta.update(f"{result.total_rows} row(s)")

    def show_error(self, message: str) -> None:
        table = self.query_one("#results-table", DataTable)
        error = self.query_one("#results-error", Label)
        meta = self.query_one("#results-meta", Label)
        table.clear(columns=True)
        meta.update("")
        error.update(message)


class ResultsWidget(Static):
    """Results panel (table view for MVP)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Results"

    def compose(self):
        yield TableResultView(id="table-view")

    def show_result(self, result: QueryResult) -> None:
        self.query_one("#table-view", TableResultView).show_result(result)

    def show_error(self, message: str) -> None:
        self.query_one("#table-view", TableResultView).show_error(message)
