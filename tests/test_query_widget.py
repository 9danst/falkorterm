from textual.app import App, ComposeResult

from falkorterm.client.models import QueryResult
from falkorterm.widgets.query import QuerySubmitted, QueryWidget
from falkorterm.widgets.results import ResultsWidget


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
                rows=((1, 2), (3, 4)),
                total_rows=2,
            )
        )
        await pilot.pause()
        table = results.query_one("#results-table")
        assert table.row_count == 2
