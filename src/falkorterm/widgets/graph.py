from __future__ import annotations

from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.widgets import Label, Static

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.explore import ExpandNeighborsRequested
from falkorterm.graph.extract import extract_graph
from falkorterm.graph.layout import EMPTY_MESSAGE, layout_ascii
from falkorterm.graph.models import GraphNode, GraphViewModel, Hitbox
from falkorterm.widgets.results import CellInspectRequested


class GraphResultView(ScrollableContainer):
    """ASCII graph rendering of a QueryResult / GraphViewModel (node select v1)."""

    can_focus = True

    BINDINGS = [
        Binding("c", "copy_canvas", "Copy graph", show=False),
    ]

    DEFAULT_CSS = """
    GraphResultView {
        height: 1fr;
        overflow-x: auto;
        overflow-y: auto;
    }
    GraphResultView #graph-canvas {
        height: auto;
        width: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model: GraphViewModel | None = None
        self._selected_index: int = 0
        self._node_order: tuple[int, ...] = ()
        self._nodes_by_id: dict[int, GraphNode] = {}
        self._hitboxes: tuple[Hitbox, ...] = ()
        self._header_lines: int = 0

    def compose(self):
        yield Label("", id="graph-meta", classes="results-meta")
        yield Static(EMPTY_MESSAGE, id="graph-canvas", markup=True)
        yield Label("", id="graph-error", classes="results-error")

    def show_model(self, model: GraphViewModel, *, result_meta: str = "") -> None:
        error = self.query_one("#graph-error", Label)
        meta = self.query_one("#graph-meta", Label)
        error.update("")
        try:
            self._model = model
            self._nodes_by_id = {n.id: n for n in model.nodes}
            self._node_order = tuple(n.id for n in model.nodes)
            if self._node_order:
                self._selected_index = min(
                    self._selected_index, len(self._node_order) - 1
                )
            else:
                self._selected_index = 0
            meta.update(result_meta)
            self._render_canvas()
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self._node_order = ()
            self._nodes_by_id = {}
            self._hitboxes = ()
            self._header_lines = 0
            self._selected_index = 0
            meta.update(result_meta)
            self.query_one("#graph-canvas", Static).update(
                f"Graph layout failed: {exc}"
            )

    def show_result(self, result: QueryResult) -> None:
        from falkorterm.widgets.results import format_result_meta

        self.show_model(
            extract_graph(result),
            result_meta=format_result_meta(result),
        )

    def show_error(self, message: str) -> None:
        canvas = self.query_one("#graph-canvas", Static)
        error = self.query_one("#graph-error", Label)
        meta = self.query_one("#graph-meta", Label)
        self._model = None
        self._node_order = ()
        self._nodes_by_id = {}
        self._hitboxes = ()
        self._header_lines = 0
        self._selected_index = 0
        meta.update("")
        canvas.update("")
        error.update(message)

    def _selected_id(self) -> int | None:
        if not self._node_order:
            return None
        return self._node_order[self._selected_index]

    def _selected_node(self) -> GraphNode | None:
        nid = self._selected_id()
        if nid is None:
            return None
        return self._nodes_by_id.get(nid)

    def _render_canvas(self) -> None:
        canvas = self.query_one("#graph-canvas", Static)
        if self._model is None or not self._model.nodes:
            canvas.update(EMPTY_MESSAGE)
            self._hitboxes = ()
            self._header_lines = 0
            return
        ascii_canvas = layout_ascii(
            self._model,
            selected_id=self._selected_id(),
        )
        self._node_order = ascii_canvas.node_order or self._node_order
        self._hitboxes = ascii_canvas.hitboxes
        self._header_lines = 1  # layout_ascii always prepends a session header
        canvas.update(
            ascii_canvas.rich if ascii_canvas.rich is not None else ascii_canvas.text
        )
        self._scroll_selection_into_view()

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key in {"up", "k"}:
            if self._move_selection(-1):
                event.prevent_default()
                event.stop()
            return
        if event.key in {"down", "j"}:
            if self._move_selection(1):
                event.prevent_default()
                event.stop()
            return
        if event.key == "enter":
            if self._inspect_selected():
                event.prevent_default()
                event.stop()
            return
        if event.key == "x":
            if self._expand_selected():
                event.prevent_default()
                event.stop()

    def _move_selection(self, delta: int) -> bool:
        if not self._node_order:
            return False
        n = len(self._node_order)
        self._selected_index = (self._selected_index + delta) % n
        self._render_canvas()
        return True

    def _scroll_selection_into_view(self) -> None:
        nid = self._selected_id()
        if nid is None:
            return
        hitbox = next((h for h in self._hitboxes if h.node_id == nid), None)
        if hitbox is None:
            return

        def _do_scroll() -> None:
            meta = self.query_one("#graph-meta", Label)
            y_base = meta.outer_size.height + self._header_lines
            view_w = max(1, self.size.width)
            view_h = max(1, self.size.height)
            target_x = max(0, hitbox.x0 - view_w // 3)
            target_y = max(0, y_base + hitbox.y0 - view_h // 2)
            self.scroll_to(x=target_x, y=target_y, animate=False, force=True)

        self.call_after_refresh(_do_scroll)

    def _inspect_selected(self) -> bool:
        node = self._selected_node()
        if node is None:
            return False
        self.post_message(
            CellInspectRequested(
                CellValue(
                    display=node.display,
                    detail={
                        "kind": "node",
                        "id": node.id,
                        "labels": list(node.labels),
                        "properties": dict(node.properties),
                    },
                )
            )
        )
        return True

    def _expand_selected(self) -> bool:
        node = self._selected_node()
        if node is None:
            return False
        self.post_message(ExpandNeighborsRequested(node.id))
        return True

    def action_copy_canvas(self) -> None:
        self.copy_canvas()

    def copy_canvas(self) -> bool:
        if self._model is None or not self._model.nodes:
            text = EMPTY_MESSAGE
        else:
            text = layout_ascii(
                self._model,
                selected_id=None,
                include_header=False,
            ).text
        self.app.copy_to_clipboard(text, what="graph")
        return True

    def copy_selected(self) -> bool:
        node = self._selected_node()
        if node is None:
            return False
        self.app.copy_to_clipboard(node.display, what="node")
        return True
