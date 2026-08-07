from textual.app import App, ComposeResult

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.screens.cell_detail import CellDetailScreen
from falkorterm.widgets.results import (
    CellInspectRequested,
    ResultsWidget,
    TableResultView,
)


class DetailHarness(App):
    def __init__(self) -> None:
        super().__init__()
        self.inspected: CellValue | None = None
        self.expanded_id: int | None = None

    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")

    def on_cell_inspect_requested(self, event: CellInspectRequested) -> None:
        self.inspected = event.cell
        self.push_screen(CellDetailScreen(event.cell))

    def on_expand_neighbors_requested(self, event: ExpandNeighborsRequested) -> None:
        self.expanded_id = event.node_id


async def test_results_enter_emits_inspect():
    app = DetailHarness()
    async with app.run_test(size=(100, 30)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        cell = CellValue(
            display="(:Person)",
            detail={
                "kind": "node",
                "labels": ["Person"],
                "properties": {"n": "Ada"},
            },
        )
        results.show_result(
            QueryResult(columns=("n",), rows=((cell,),), total_rows=1)
        )
        await pilot.pause()
        view = results.query_one("#table-view", TableResultView)
        view._inspect_coordinate(0, 0)
        await pilot.pause()
        assert app.inspected is not None
        assert app.inspected.detail is not None
        assert app.inspected.detail["kind"] == "node"
        assert isinstance(app.screen, CellDetailScreen)
        assert list(app.screen.query("#btn-expand-neighbors")) == []


async def test_cell_detail_screen_renders_tabs_and_header():
    cell = CellValue(
        display="(:Person id=7)",
        detail={
            "kind": "node",
            "id": 7,
            "labels": ["Person"],
            "properties": {"a": 1},
        },
    )

    class Harness(App):
        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

    h = Harness()
    async with h.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        assert h.screen.query_one("#cell-detail-tabs")
        assert h.screen.query_one("#cell-detail-props")
        assert h.screen.query_one("#cell-detail-tree")
        header = str(h.screen.query_one("#cell-detail-header").render())
        assert "node" in header
        assert "id=7" in header
        assert "Person" in header
        table = h.screen.query_one("#cell-detail-props")
        assert table.row_count == 1
        assert table.get_cell_at((0, 0)) == "a"
        assert table.get_cell_at((0, 1)) == "1"


async def test_cell_detail_toggle_tab():
    cell = CellValue(
        display="x",
        detail={"kind": "node", "properties": {"a": 1}},
    )

    class Harness(App):
        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

    h = Harness()
    async with h.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        screen = h.screen
        assert isinstance(screen, CellDetailScreen)
        tabs = screen.query_one("#cell-detail-tabs")
        assert tabs.active == "tab-properties"
        screen.action_toggle_tab()
        await pilot.pause()
        assert tabs.active == "tab-json"
        screen.action_toggle_tab()
        await pilot.pause()
        assert tabs.active == "tab-properties"


async def test_cell_detail_copy_selected_value():
    cell = CellValue(
        display="x",
        detail={"kind": "node", "properties": {"name": "Ada"}},
    )

    class Harness(App):
        def __init__(self) -> None:
            super().__init__()
            self.clipboard_log: list[tuple[str, str]] = []

        def copy_to_clipboard(self, text: str, *, what: str = "text") -> None:  # type: ignore[override]
            self.clipboard_log.append((text, what))

        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

    h = Harness()
    async with h.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        screen = h.screen
        assert isinstance(screen, CellDetailScreen)
        table = screen.query_one("#cell-detail-props")
        table.focus()
        table.move_cursor(row=0, column=1)
        await pilot.pause()
        screen.action_copy()
        assert h.clipboard_log[-1] == ("Ada", "value")



async def test_cell_detail_expand_emits_message():
    cell = CellValue(
        display="(:Person id=7)",
        detail={"kind": "node", "id": 7, "labels": ["Person"], "properties": {}},
    )

    class Harness(App):
        def __init__(self) -> None:
            super().__init__()
            self.expanded_id: int | None = None

        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

        def on_expand_neighbors_requested(
            self, event: ExpandNeighborsRequested
        ) -> None:
            self.expanded_id = event.node_id

    h = Harness()
    async with h.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert h.screen.query_one("#btn-expand-neighbors")
        h.screen.action_expand()
        await pilot.pause()
        assert h.expanded_id == 7
