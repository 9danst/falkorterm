from falkorterm.app import FalkorTerm
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.widgets.query import QuerySubmitted, QueryWidget


class FakeClient:
    """Minimal client stand-in for binding tests."""

    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self.calls: list[str] = []

    def connect(self, config: ConnectionConfig) -> None:
        self.connected = True
        self.config = config

    def list_graphs(self) -> list[str]:
        return [config.graph if (config := self.config) else "test"]

    def select_graph(self, name: str) -> None:
        from dataclasses import replace

        assert self.config is not None
        self.config = replace(self.config, graph=name)

    def get_schema(self) -> GraphSchema:
        return GraphSchema(labels=("Person",), relations=("KNOWS",))

    def run_query(self, cypher: str) -> QueryResult:
        self.calls.append(cypher)
        return QueryResult(
            columns=("n",),
            rows=((CellValue("Node[1]"),),),
            total_rows=1,
            elapsed_ms=1.5,
        )


async def _connect_via_screen(pilot, app: FalkorTerm) -> None:
    await pilot.pause()
    screen = app.screen
    from falkorterm.screens.connection import ConnectionScreen

    assert isinstance(screen, ConnectionScreen)
    screen._on_open()
    await pilot.pause()


async def _submit_calls_for_key(key: str) -> list[str]:
    """Press a key with the query focused; return texts passed to submit()."""
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    calls: list[str] = []
    async with app.run_test(size=(120, 40)) as pilot:
        await _connect_via_screen(pilot, app)
        await pilot.press("ctrl+3")
        query = app.query_one("#query", QueryWidget)
        query.set_text("MATCH (n) RETURN n")

        def spy_submit() -> None:
            calls.append(query.get_text().strip())

        query.submit = spy_submit  # type: ignore[method-assign]
        await pilot.press(key)
        await pilot.pause()
    return calls


async def test_ctrl_enter_runs_query():
    assert await _submit_calls_for_key("ctrl+enter") == ["MATCH (n) RETURN n"]


async def test_ctrl_j_runs_query_as_terminal_ctrl_enter():
    """Most terminals send \\n (ctrl+j) for Ctrl+Enter, not ctrl+enter."""
    assert await _submit_calls_for_key("ctrl+j") == ["MATCH (n) RETURN n"]


async def test_app_sets_running_indicator():
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await _connect_via_screen(pilot, app)
        query = app.query_one("#query", QueryWidget)
        # Avoid worker/thread side effects; only exercise indicator wiring.
        app._execute_query = lambda cypher, gen: None  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("RETURN 1"))
        await pilot.pause()
        assert query.has_class("running")
        assert query.border_title == "Cypher query · Running…"
        app._clear_running()
        await pilot.pause()
        assert not query.has_class("running")
        assert query.border_title == "Cypher query"


async def test_ctrl_j_shows_results_in_table():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await _connect_via_screen(pilot, app)
        query = app.query_one("#query", QueryWidget)
        query.set_text("MATCH (n) RETURN n")
        await pilot.press("ctrl+3")
        await pilot.press("ctrl+j")
        for _ in range(20):
            await pilot.pause(0.05)
            table = app.query_one("#results-table")
            if table.row_count > 0:
                break
        assert client.calls == ["MATCH (n) RETURN n"]
        assert app.query_one("#results-table").row_count == 1
        assert not query.has_class("running")
        from falkorterm.app import StatusBar

        status = app.query_one("#status", StatusBar)
        assert "1 row" in str(status.content)
        assert "1.5ms" in str(status.content)
        assert "connected" in str(status.content)
