from textual.app import App, ComposeResult
from textual.widgets import Label

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.widgets.query import QuerySubmitted, QueryWidget
from falkorterm.widgets.results import (
    ResultsWidget,
    format_elapsed_ms,
    format_result_meta,
)


class QueryHarness(App):
    def compose(self) -> ComposeResult:
        yield QueryWidget(id="query")

    def on_query_submitted(self, event: QuerySubmitted) -> None:
        self.submitted = event.cypher


async def test_query_submit_emits_message():
    app = QueryHarness()
    async with app.run_test() as pilot:
        query = app.query_one("#query", QueryWidget)
        query.set_text("MATCH (n) RETURN n")
        query.submit()
        await pilot.pause()
        assert app.submitted == "MATCH (n) RETURN n"


async def test_set_running_toggles_title_and_class():
    app = QueryHarness()
    async with app.run_test() as pilot:
        query = app.query_one("#query", QueryWidget)
        assert query.border_title == "Cypher query"
        assert query.border_subtitle == "Ctrl+Enter · ↑↓ history · F4 help"
        assert not query.has_class("running")

        query.set_running(True)
        await pilot.pause()
        assert query.border_title == "Cypher query · Running…"
        assert query.border_subtitle == "Esc cancel (disconnects query)"
        assert query.has_class("running")

        query.set_running(False)
        await pilot.pause()
        assert query.border_title == "Cypher query"
        assert query.border_subtitle == "Ctrl+Enter · ↑↓ history · F4 help"
        assert not query.has_class("running")


class ResultsHarness(App):
    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")


async def test_results_show_rows():
    app = ResultsHarness()
    async with app.run_test() as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "b"),
                rows=(
                    (CellValue("1"), CellValue("2")),
                    (CellValue("3"), CellValue("4")),
                ),
                total_rows=2,
                elapsed_ms=8.4,
            )
        )
        await pilot.pause()
        table = results.query_one("#results-table")
        assert table.row_count == 2
        meta = results.query_one("#results-meta", Label)
        assert "2 rows" in str(meta.content)
        assert "8.4ms" in str(meta.content)
        assert results.border_title == "Results · 2"
        assert results.border_subtitle == "8.4ms"


async def test_results_show_truncated_meta():
    app = ResultsHarness()
    async with app.run_test() as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a",),
                rows=((CellValue("1"),), (CellValue("2"),)),
                total_rows=1200,
                truncated=True,
                elapsed_ms=45.0,
            )
        )
        await pilot.pause()
        meta = results.query_one("#results-meta", Label)
        text = str(meta.content)
        assert "Showing 2 of 1200" in text
        assert "45.0ms" in text
        assert "truncated" in text
        assert results.border_title == "Results · 2/1200"


def test_format_elapsed_ms():
    assert format_elapsed_ms(None) is None
    assert format_elapsed_ms(12.34) == "12.3ms"
    assert format_elapsed_ms(1500) == "1.5s"


def test_format_result_meta():
    result = QueryResult(
        columns=("n",),
        rows=((CellValue("1"),),),
        total_rows=1,
        elapsed_ms=8.4,
    )
    assert format_result_meta(result) == "1 row · 8.4ms"
