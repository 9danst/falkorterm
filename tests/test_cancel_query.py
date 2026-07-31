from falkorterm.app import FalkorTerm, StatusBar
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.screens.connection import ConnectionScreen
from falkorterm.widgets.query import QuerySubmitted, QueryWidget


class FakeClient:
    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self.abort_called = False

    def connect(self, config: ConnectionConfig) -> None:
        self.connected = True
        self.config = config

    def list_graphs(self) -> list[str]:
        return ["test"]

    def select_graph(self, name: str) -> None:
        from dataclasses import replace

        assert self.config is not None
        self.config = replace(self.config, graph=name)

    def get_schema(self) -> GraphSchema:
        return GraphSchema(labels=(), relations=())

    def run_query(self, cypher: str) -> QueryResult:
        return QueryResult(
            columns=("n",),
            rows=((CellValue("ok"),),),
            total_rows=1,
            elapsed_ms=1.0,
        )

    def abort_and_reconnect(self) -> None:
        self.abort_called = True


async def test_cancel_query_bumps_generation_and_clears_running():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test"),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen._on_open()
        await pilot.pause()

        query = app.query_one("#query", QueryWidget)
        app._execute_query = lambda cypher, gen: None  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("RETURN 1"))
        await pilot.pause()
        assert app._query_running
        gen_before = app._query_generation

        app.action_cancel_query()
        await pilot.pause()
        assert not app._query_running
        assert app._query_generation == gen_before + 1
        assert not query.has_class("running")
        assert client.abort_called
        status = app.query_one("#status", StatusBar)
        assert "cancelled" in str(status.content)
        assert "reconnected" in str(status.content)


async def test_stale_success_is_ignored():
    app = FalkorTerm(
        config=ConnectionConfig(graph="test"),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ConnectionScreen)
        app.screen._on_open()
        await pilot.pause()

        app._query_generation = 2
        result = QueryResult(
            columns=("n",),
            rows=((CellValue("stale"),),),
            total_rows=1,
        )
        app._on_query_success(1, result)
        await pilot.pause()
        assert app.query_one("#results-table").row_count == 0
