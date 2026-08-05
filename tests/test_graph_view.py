from textual.app import App, ComposeResult
from textual.widgets import Static

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.graph.colors import EMPTY_MESSAGE
from falkorterm.widgets.graph import GraphResultView
from falkorterm.widgets.results import GRAPH_HINT, CellInspectRequested, ResultsWidget
from falkorterm.widgets.surf import SurfView


def _node(nid: int, label: str = "Person") -> CellValue:
    return CellValue(
        display=f"(:{label} id={nid})",
        detail={
            "kind": "node",
            "id": nid,
            "labels": [label],
            "properties": {},
        },
    )


def _edge(src: int, dest: int, rel: str = "KNOWS") -> CellValue:
    return CellValue(
        display=f"-[:{rel}]->",
        detail={
            "kind": "edge",
            "type": rel,
            "src": src,
            "dest": dest,
            "properties": {},
        },
    )


class GraphHarness(App):
    def __init__(self) -> None:
        super().__init__()
        self.inspected: CellValue | None = None
        self.expanded_id: int | None = None

    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")

    def on_cell_inspect_requested(self, event: CellInspectRequested) -> None:
        self.inspected = event.cell

    def on_expand_neighbors_requested(self, event: ExpandNeighborsRequested) -> None:
        self.expanded_id = event.node_id


async def test_g_cycles_table_graph_surf():
    app = GraphHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        assert results.mode == "table"

        results.focus_active_view()
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        assert results.mode == "graph"
        graph = results.query_one("#graph-view", GraphResultView)
        canvas = str(graph.query_one("#graph-canvas", Static).render())
        assert "id=1" in canvas
        assert "id=2" in canvas
        assert "[:KNOWS]" in canvas or "KNOWS" in canvas

        await pilot.press("g")
        await pilot.pause()
        assert results.mode == "surf"
        surf = results.query_one("#surf-view", SurfView)
        surf_canvas = str(surf.query_one("#surf-canvas", Static).render())
        assert "FOCUS" in surf_canvas
        assert "id=1" in surf_canvas

        await pilot.press("g")
        await pilot.pause()
        assert results.mode == "table"


async def test_graph_empty_for_scalars():
    app = GraphHarness()
    async with app.run_test(size=(100, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("n",),
                rows=((CellValue(display="1"),),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        canvas = str(
            results.query_one("#graph-view", GraphResultView)
            .query_one("#graph-canvas", Static)
            .render()
        )
        assert EMPTY_MESSAGE in canvas


async def test_manual_query_seeds_surf_expand_merges_ascii_replaces():
    app = GraphHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()

        surf = results.query_one("#surf-view", SurfView)
        assert surf._session is not None
        assert surf._session.model is not None
        assert {node.id for node in surf._session.model.nodes} == {1, 2}

        results.begin_expand_merge(1)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 3, "LIKES"), _node(3)),),
                total_rows=1,
            )
        )
        await pilot.pause()

        assert surf._session.model is not None
        assert {node.id for node in surf._session.model.nodes} == {1, 2, 3}
        graph = results.query_one("#graph-view", GraphResultView)
        assert graph._model is not None
        assert {node.id for node in graph._model.nodes} == {1, 3}

        results.begin_expand_merge(1)
        results.prepare_manual_query()
        results.show_result(
            QueryResult(
                columns=("n",),
                rows=((_node(4),),),
                total_rows=1,
            )
        )
        await pilot.pause()

        assert surf._session.model is not None
        assert {node.id for node in surf._session.model.nodes} == {4}


async def test_graph_enter_inspects_node():
    app = GraphHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        graph = results.query_one("#graph-view", GraphResultView)
        graph.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.inspected is not None
        assert app.inspected.detail is not None
        assert app.inspected.detail["kind"] == "node"


async def test_graph_x_expands_selected_node():
    app = GraphHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        assert "x expand" in results.border_subtitle
        graph = results.query_one("#graph-view", GraphResultView)
        graph.focus()
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        assert app.expanded_id == 1


async def test_graph_hint_and_copy():
    app = GraphHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
                elapsed_ms=12.0,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        assert GRAPH_HINT in results.border_subtitle
        assert "↑↓" in results.border_subtitle


class GraphCopyHarness(App):
    def __init__(self) -> None:
        super().__init__()
        self.clipboard_log: list[str] = []

    def copy_to_clipboard(self, text: str, *, what: str = "text") -> None:  # type: ignore[override]
        self.clipboard_log.append(text)

    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")


async def test_c_copies_ascii_from_graph():
    app = GraphCopyHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        results.focus_active_view()
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert app.clipboard_log
        assert "id=1" in app.clipboard_log[-1]
        assert "id=2" in app.clipboard_log[-1]
