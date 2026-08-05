from textual.app import App, ComposeResult

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.screens.cell_detail import CellDetailScreen
from falkorterm.widgets.query import QueryWidget
from falkorterm.widgets.results import ResultsWidget, TableResultView


class CopyHarness(App):
    def __init__(self) -> None:
        super().__init__()
        self.clipboard_log: list[str] = []

    def copy_to_clipboard(self, text: str, *, what: str = "text") -> None:  # type: ignore[override]
        self.clipboard_log.append(text)

    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")
        yield QueryWidget(id="query")


async def test_copy_cell_and_row():
    app = CopyHarness()
    async with app.run_test(size=(100, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "b"),
                rows=((CellValue("hello"), CellValue("world")),),
                total_rows=1,
            )
        )
        await pilot.pause()
        view = results.query_one("#table-view", TableResultView)
        table = view.query_one("#results-table")
        table.focus()
        table.move_cursor(row=0, column=0)
        await pilot.pause()
        assert view.copy_cell()
        assert app.clipboard_log[-1] == "hello"
        assert view.copy_row()
        assert app.clipboard_log[-1] == "hello\tworld"


async def test_copy_query():
    app = CopyHarness()
    async with app.run_test(size=(100, 40)) as pilot:
        query = app.query_one("#query", QueryWidget)
        query.set_text("RETURN 1")
        await pilot.pause()
        query.action_copy_query()
        assert app.clipboard_log[-1] == "RETURN 1"


async def test_cell_detail_copy():
    cell = CellValue(display="x", detail={"kind": "node", "properties": {"a": 1}})

    class Harness(App):
        def __init__(self) -> None:
            super().__init__()
            self.clipboard_log: list[str] = []

        def copy_to_clipboard(self, text: str, *, what: str = "text") -> None:  # type: ignore[override]
            self.clipboard_log.append(text)

        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

    h = Harness()
    async with h.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        screen = h.screen
        assert isinstance(screen, CellDetailScreen)
        screen.action_copy()
        assert '"kind": "node"' in h.clipboard_log[-1]
        assert screen.copy_text().startswith("{")
