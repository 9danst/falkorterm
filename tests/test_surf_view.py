from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from falkorterm.client.models import CellValue
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.session import SurfSession
from falkorterm.widgets.results import CellInspectRequested
from falkorterm.widgets.surf import SurfView


def _session() -> SurfSession:
    session = SurfSession()
    session.seed(
        GraphViewModel(
            nodes=(
                GraphNode(id=1, labels=("P",), properties={"name": "A"}, display="A"),
                GraphNode(id=2, labels=("P",), properties={"name": "B"}, display="B"),
                GraphNode(id=3, labels=("P",), properties={"name": "C"}, display="C"),
            ),
            edges=(
                GraphEdge(src=1, dest=2, type="KNOWS", id=10),
                GraphEdge(src=3, dest=1, type="FOLLOWS", id=11),
            ),
            total_nodes=3,
            total_edges=2,
        )
    )
    return session


class SurfApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.expanded_id: int | None = None
        self.inspected: CellValue | None = None
        self.clipboard_log: list[str] = []

    def compose(self) -> ComposeResult:
        yield SurfView(id="surf")

    def on_expand_neighbors_requested(self, event: ExpandNeighborsRequested) -> None:
        self.expanded_id = event.node_id

    def on_cell_inspect_requested(self, event: CellInspectRequested) -> None:
        self.inspected = event.cell

    def copy_to_clipboard(self, text: str, *, what: str = "text") -> None:  # type: ignore[override]
        self.clipboard_log.append(text)


class SurfWithGlobalOpenApp(SurfApp):
    BINDINGS = [Binding("ctrl+o", "open_connection", "Connect")]

    def __init__(self) -> None:
        super().__init__()
        self.opened = 0

    def action_open_connection(self) -> None:
        self.opened += 1


async def test_j_cycles_neighbor_and_enter_hops():
    session = _session()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("j")
        await pilot.pause()
        assert session.neighbor_index == 0

        await pilot.press("enter")
        await pilot.pause()
        assert session.focus_id == 2
        assert session.neighbor_index == -1
        canvas = str(surf.query_one("#surf-canvas", Static).render())
        assert "FOCUS" in canvas
        assert "B" in canvas


async def test_x_posts_expand_for_focus_node():
    session = _session()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("j")
        await pilot.press("x")
        await pilot.pause()

        assert app.expanded_id == 1


async def test_h_and_ctrl_i_move_jump_history():
    session = _session()
    session.cycle_neighbor(1)
    session.hop()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("h")
        await pilot.pause()
        assert session.focus_id == 1

        await pilot.press("ctrl+i")
        await pilot.pause()
        assert session.focus_id == 2


async def test_shift_l_moves_jump_history_forward():
    session = _session()
    session.cycle_neighbor(1)
    session.hop()
    session.jump_back()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("L")
        await pilot.pause()

        assert session.focus_id == 2


async def test_ctrl_o_with_no_history_is_consumed_by_surf():
    session = _session()
    app = SurfWithGlobalOpenApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("ctrl+o")
        await pilot.pause()

        assert session.focus_id == 1
        assert session.jump_index == 0
        assert app.opened == 0


async def test_tab_toggles_kind_and_rerenders_edge_selection():
    session = _session()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("j")
        await pilot.press("tab")
        await pilot.pause()

        assert session.select_kind == "edge"
        canvas = str(surf.query_one("#surf-canvas", Static).render())
        assert "«KNOWS»" in canvas


async def test_enter_on_focus_inspects_focus_node():
    session = _session()
    app = SurfApp()
    async with app.run_test(size=(100, 30)) as pilot:
        surf = app.query_one("#surf", SurfView)
        surf.set_session(session)
        surf.focus()
        await pilot.pause()

        await pilot.press("enter")
        await pilot.pause()

        assert app.inspected is not None
        assert app.inspected.detail is not None
        assert app.inspected.detail["kind"] == "node"
        assert app.inspected.detail["id"] == 1
