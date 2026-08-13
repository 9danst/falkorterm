from falkorterm.app import FalkorTerm
from falkorterm.client.models import (
    ConnectionConfig,
    FalkorConnectionError,
    GraphSchema,
    QueryResult,
)
from falkorterm.screens.connection import ConnectionScreen


class FakeClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self.fail = fail

    def connect(self, config: ConnectionConfig) -> None:
        if self.fail:
            raise FalkorConnectionError("refused")
        self.connected = True
        self.config = config

    def list_graphs(self) -> list[str]:
        return ["test"]

    def get_schema(self) -> GraphSchema:
        return GraphSchema(labels=("Person",), relations=("KNOWS",))

    def run_query(self, cypher: str) -> QueryResult:
        return QueryResult(columns=("n",), rows=(), total_rows=0)


async def test_skip_connect_bypasses_connection_screen():
    client = FakeClient()
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=client,  # type: ignore[arg-type]
        skip_connect=True,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert not isinstance(app.screen, ConnectionScreen)
        assert client.connected
        assert app._connection_ok is True


async def test_skip_connect_falls_back_on_failure():
    client = FakeClient(fail=True)
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=client,  # type: ignore[arg-type]
        skip_connect=True,
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ConnectionScreen)
        assert client.connected is False
        assert app._connection_ok is False
