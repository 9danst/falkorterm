from __future__ import annotations

from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from falkorterm.client.models import CellValue
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.graph.colors import EMPTY_MESSAGE
from falkorterm.graph.models import GraphEdge, GraphNode
from falkorterm.graph.render_surf import render_surf
from falkorterm.graph.session import SurfSession
from falkorterm.widgets.results import CellInspectRequested


class SurfView(VerticalScroll):
    """Keyboard ego-hop inspector (Surf mode)."""

    can_focus = True

    BINDINGS = [
        Binding("x", "expand", "Expand", show=False),
        Binding("c", "copy", "Copy", show=False),
        Binding("y", "copy_selection", "Yank", show=False),
    ]

    DEFAULT_CSS = """
    SurfView {
        height: 1fr;
    }
    SurfView #surf-canvas {
        height: auto;
        width: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session: SurfSession | None = None

    def compose(self):
        yield Static(EMPTY_MESSAGE, id="surf-canvas")

    def set_session(self, session: SurfSession) -> None:
        self._session = session
        self.refresh_from_session()

    def show_session(self, session: SurfSession) -> None:
        self.set_session(session)

    def clear_session(self) -> None:
        self._session = None
        self.query_one("#surf-canvas", Static).update(EMPTY_MESSAGE)

    def show_error(self, message: str) -> None:
        self._session = None
        self.query_one("#surf-canvas", Static).update(message)

    def refresh_from_session(self) -> None:
        canvas = self.query_one("#surf-canvas", Static)
        if self._session is None:
            canvas.update(EMPTY_MESSAGE)
            return
        canvas.update(render_surf(self._session))

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key in {"down", "j"}:
            handled = self._cycle_neighbor(1)
        elif event.key in {"up", "k"}:
            handled = self._cycle_neighbor(-1)
        elif event.key == "l":
            handled = self._hop()
        elif event.key == "enter":
            handled = self._activate_enter()
        elif event.key in {"h", "ctrl+o"}:
            handled = self._jump_back()
        elif event.key == "ctrl+i":
            handled = self._jump_forward()
        elif event.key == "tab":
            handled = self._toggle_kind()
        elif event.key == "x":
            handled = self._expand_focus()
        elif event.key == "y":
            handled = self.copy_selection()
        else:
            return

        if handled:
            event.prevent_default()
            event.stop()

    def _cycle_neighbor(self, delta: int) -> bool:
        if self._session is None:
            return False
        if not self._session.cycle_neighbor(delta):
            return False
        self.refresh_from_session()
        return True

    def _hop(self) -> bool:
        if self._session is None:
            return False
        if not self._session.hop():
            return False
        self.refresh_from_session()
        return True

    def _activate_enter(self) -> bool:
        if self._session is None:
            return False
        if self._session.neighbor_index >= 0:
            return self._hop()
        return self._inspect_focus()

    def _jump_back(self) -> bool:
        if self._session is None:
            return False
        if not self._session.jump_back():
            return False
        self.refresh_from_session()
        return True

    def _jump_forward(self) -> bool:
        if self._session is None:
            return False
        if not self._session.jump_forward():
            return False
        self.refresh_from_session()
        return True

    def _toggle_kind(self) -> bool:
        if self._session is None:
            return False
        if not self._session.toggle_kind():
            return False
        self.refresh_from_session()
        return True

    def action_expand(self) -> None:
        self._expand_focus()

    def _expand_focus(self) -> bool:
        session = self._session
        if session is None or session.focus_id is None:
            return False
        self.post_message(ExpandNeighborsRequested(session.focus_id))
        return True

    def _inspect_focus(self) -> bool:
        session = self._session
        if session is None:
            return False
        node = session.focus_node()
        if node is None:
            return False
        self.post_message(CellInspectRequested(_node_cell(node)))
        return True

    def action_copy(self) -> None:
        self.copy_canvas()

    def copy_canvas(self) -> bool:
        if self._session is None:
            text = EMPTY_MESSAGE
        else:
            text = render_surf(self._session).plain
            text = text.replace("▸ ", "  ").replace("«", "[:").replace("»", "]")
        self.app.copy_to_clipboard(text, what="surf")
        return True

    def action_copy_selection(self) -> None:
        self.copy_selection()

    def copy_selection(self) -> bool:
        cell = self._selected_cell()
        if cell is None:
            return False
        self.app.copy_to_clipboard(cell.display, what="surf selection")
        return True

    def _selected_cell(self) -> CellValue | None:
        session = self._session
        if session is None:
            return None
        if session.neighbor_index >= 0 and session.select_kind == "edge":
            edge = session.current_edge()
            return _edge_cell(edge) if edge is not None else None
        if session.neighbor_index >= 0:
            node_id = session.current_neighbor_id()
            node = _node_by_id(session, node_id)
            return _node_cell(node) if node is not None else None
        node = session.focus_node()
        return _node_cell(node) if node is not None else None


def _node_by_id(session: SurfSession, node_id: int | None) -> GraphNode | None:
    if session.model is None or node_id is None:
        return None
    for node in session.model.nodes:
        if node.id == node_id:
            return node
    return None


def _node_cell(node: GraphNode) -> CellValue:
    return CellValue(
        display=node.display,
        detail={
            "kind": "node",
            "id": node.id,
            "labels": list(node.labels),
            "properties": dict(node.properties),
        },
    )


def _edge_cell(edge: GraphEdge) -> CellValue:
    display = f"({edge.src})-[:{edge.type}]->({edge.dest})"
    return CellValue(
        display=display,
        detail={
            "kind": "edge",
            "src": edge.src,
            "dest": edge.dest,
            "type": edge.type,
            "properties": dict(edge.properties),
        },
    )
