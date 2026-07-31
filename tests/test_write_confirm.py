from falkorterm.app import FalkorTerm, StatusBar
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.screens.confirm import ConfirmScreen
from falkorterm.screens.connection import ConnectionScreen
from falkorterm.widgets.query import QuerySubmitted, QueryWidget


class FakeClient:
    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self.queries: list[str] = []

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
        self.queries.append(cypher)
        return QueryResult(
            columns=("n",),
            rows=((CellValue("ok"),),),
            total_rows=1,
            elapsed_ms=1.0,
        )


async def test_write_query_shows_confirm_and_runs_on_yes():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test"),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ConnectionScreen)
        app.screen._on_open()
        await pilot.pause()

        started: list[str] = []
        app._start_query = lambda cypher: started.append(cypher)  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("CREATE (n:Person)"))
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        assert started == []
        app.screen.action_yes()
        await pilot.pause()
        assert started == ["CREATE (n:Person)"]


async def test_write_query_cancel_does_not_run():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test"),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._on_open()
        await pilot.pause()

        started: list[str] = []
        app._start_query = lambda cypher: started.append(cypher)  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("DELETE n"))
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        app.screen.action_no()
        await pilot.pause()
        assert started == []
        assert not app._query_running


async def test_read_query_skips_confirm():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test"),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._on_open()
        await pilot.pause()

        started: list[str] = []
        app._start_query = lambda cypher: started.append(cypher)  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("MATCH (n) RETURN n"))
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmScreen)
        assert started == ["MATCH (n) RETURN n"]
