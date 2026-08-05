from textual.app import App, ComposeResult
from textual.widgets import Static

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.widgets.graph import GraphResultView
from falkorterm.widgets.results import ResultsWidget


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


def _edge(src: int, dest: int, rel: str = "KNOWS", eid: int | None = None) -> CellValue:
    detail: dict[str, object] = {
        "kind": "edge",
        "type": rel,
        "src": src,
        "dest": dest,
        "properties": {},
    }
    if eid is not None:
        detail["id"] = eid
    return CellValue(display=f"-[:{rel}]->", detail=detail)


class SessionHarness(App):
    def compose(self) -> ComposeResult:
        yield ResultsWidget(id="results")


async def test_show_result_replaces_graph_model():
    """v1: each result replaces the ASCII graph (no session merge)."""
    app = SessionHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a", "r", "b"),
                rows=((_node(1), _edge(1, 2, eid=9), _node(2)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.action_toggle_graph()
        await pilot.pause()
        graph = results.query_one("#graph-view", GraphResultView)
        assert graph._model is not None
        assert {n.id for n in graph._model.nodes} == {1, 2}

        results.begin_expand_merge(2)  # no-op in v1
        results.show_result(
            QueryResult(
                columns=("n", "r", "m"),
                rows=((_node(2), _edge(2, 3, eid=10), _node(3)),),
                total_rows=1,
            )
        )
        await pilot.pause()
        assert graph._model is not None
        assert {n.id for n in graph._model.nodes} == {2, 3}
        canvas = str(graph.query_one("#graph-canvas", Static).render())
        assert "id=2" in canvas
        assert "id=3" in canvas
        assert "id=1" not in canvas


async def test_show_error_clears_graph():
    app = SessionHarness()
    async with app.run_test(size=(100, 40)) as pilot:
        results = app.query_one("#results", ResultsWidget)
        results.show_result(
            QueryResult(
                columns=("a",),
                rows=((_node(1),),),
                total_rows=1,
            )
        )
        await pilot.pause()
        results.show_error("boom")
        await pilot.pause()
        graph = results.query_one("#graph-view", GraphResultView)
        assert graph._model is None
        assert results.graph_focus_id is None
