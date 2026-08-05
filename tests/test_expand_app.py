from falkorterm.app import FalkorTerm
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.explore import ExpandNeighborsRequested, neighbors_cypher
from falkorterm.screens.connection import ConnectionScreen
from falkorterm.widgets.query import QueryWidget


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


async def test_expand_neighbors_inserts_and_runs():
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
        app.on_expand_neighbors_requested(ExpandNeighborsRequested(9))
        await pilot.pause()
        expected = neighbors_cypher(9)
        assert app.query_one("#query", QueryWidget).get_text() == expected
        assert started == [expected]
        assert app.query_one("#results").graph_focus_id is None
