from falkorterm.app import FalkorTerm, status_target
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.screens.confirm import ConfirmScreen
from falkorterm.screens.connection import ConnectionScreen
from falkorterm.widgets.query import QuerySubmitted
from falkorterm.widgets.results import ResultsWidget


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


def test_status_target_read_only():
    assert status_target(ConnectionConfig(graph="g")) == "g@localhost:6379"
    assert (
        status_target(ConnectionConfig(graph="g", read_only=True))
        == "g@localhost:6379 · read-only"
    )


async def test_write_blocked_in_read_only():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test", read_only=True),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ConnectionScreen)
        app.screen.query_one("#conn-read-only").value = True
        app.screen._on_open()
        await pilot.pause()

        started: list[str] = []
        app._start_query = lambda cypher: started.append(cypher)  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("CREATE (n:Person)"))
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmScreen)
        assert started == []
        assert client.queries == []
        error = str(app.query_one("#results", ResultsWidget).query_one("#results-error").render())
        assert "Read-only" in error


async def test_write_still_confirms_when_not_read_only():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(graph="test", read_only=False),
        client=client,  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._on_open()
        await pilot.pause()

        started: list[str] = []
        app._start_query = lambda cypher: started.append(cypher)  # type: ignore[method-assign]
        app.on_query_submitted(QuerySubmitted("CREATE (n:Person)"))
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        assert started == []
