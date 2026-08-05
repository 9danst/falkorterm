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


async def test_cell_detail_screen_renders_json():
    cell = CellValue(display="x", detail={"kind": "node", "properties": {"a": 1}})

    class Harness(App):
        def on_mount(self) -> None:
            self.push_screen(CellDetailScreen(cell))

    h = Harness()
    async with h.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        body = h.screen.query_one("#cell-detail-body")
        text = str(body.render())
        assert "properties" in text
        assert "1" in text


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
