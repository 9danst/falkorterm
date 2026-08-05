from falkorterm.app import FalkorTerm
from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult
from falkorterm.widgets.query import QueryWidget


class FakeClient:
    """Minimal client stand-in for focus binding tests."""

    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None

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
        return QueryResult(
            columns=("n",),
            rows=((CellValue("Node[1]"),),),
            total_rows=1,
            elapsed_ms=1.0,
        )


async def _connect_via_screen(pilot, app: FalkorTerm) -> None:
    await pilot.pause()
    from falkorterm.screens.connection import ConnectionScreen

    assert isinstance(app.screen, ConnectionScreen)
    app.screen._on_open()
    await pilot.pause()


async def _assert_focus_cycle(pilot, app: FalkorTerm, query_key: str, context_key: str, results_key: str) -> None:
    await pilot.press(query_key)
    await pilot.pause()
    assert app.focused is not None
    assert app.focused.id == "cypher-input"

    await pilot.press(context_key)
    await pilot.pause()
    assert app.focused is not None
    assert app.focused.id == "labels-list"

    await pilot.press(results_key)
    await pilot.pause()
    assert app.focused is not None
    assert app.focused.id == "results-table"

    # From results, return to query and confirm bindings still work
    # while the TextArea has focus.
    await pilot.press(query_key)
    await pilot.pause()
    query = app.query_one("#query", QueryWidget)
    assert app.focused is query.query_one("#cypher-input")

    await pilot.press(context_key)
    await pilot.pause()
    assert app.focused is not None
    assert app.focused.id == "labels-list"


async def test_f_keys_focus_bindings_move_focus():
    """F1/F2/F3 are universally delivered by terminals (unlike Ctrl+digit)."""
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await _connect_via_screen(pilot, app)
        await _assert_focus_cycle(pilot, app, "f3", "f1", "f2")


async def test_ctrl_number_focus_bindings_move_focus_when_terminal_emits_them():
    """Ctrl+1/2/3 work in Kitty-style terminals; keep as aliases."""
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="test"),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await _connect_via_screen(pilot, app)
        await _assert_focus_cycle(pilot, app, "ctrl+3", "ctrl+1", "ctrl+2")
