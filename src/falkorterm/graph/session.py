from __future__ import annotations

from dataclasses import dataclass, field

from falkorterm.graph.extract import edge_key
from falkorterm.graph.merge import merge_graphs
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


@dataclass(frozen=True)
class NeighborEntry:
    edge: GraphEdge
    other_id: int
    direction: str  # "out" | "in"


@dataclass
class SurfSession:
    model: GraphViewModel | None = None
    focus_id: int | None = None
    neighbor_index: int = -1
    select_kind: str = "node"  # "node" | "edge"
    jump_list: list[int] = field(default_factory=list)
    jump_index: int = -1
    seed_id: int | None = None

    def clear(self) -> None:
        self.model = None
        self.focus_id = None
        self.neighbor_index = -1
        self.select_kind = "node"
        self.jump_list = []
        self.jump_index = -1
        self.seed_id = None

    def seed(self, model: GraphViewModel) -> None:
        self.model = model
        self.select_kind = "node"
        self.neighbor_index = -1
        if not model.nodes:
            self.focus_id = None
            self.seed_id = None
            self.jump_list = []
            self.jump_index = -1
            return
        self.focus_id = model.nodes[0].id
        self.seed_id = self.focus_id
        self.jump_list = [self.focus_id]
        self.jump_index = 0

    def merge(self, incoming: GraphViewModel) -> None:
        if self.model is None:
            self.seed(incoming)
            return
        self.model = merge_graphs(self.model, incoming)
        ids = {n.id for n in self.model.nodes}
        if self.focus_id not in ids:
            self.focus_id = self.model.nodes[0].id if self.model.nodes else None
        self._clamp_neighbor()

    def neighbors(self) -> list[NeighborEntry]:
        if self.model is None or self.focus_id is None:
            return []
        nodes = {n.id for n in self.model.nodes}
        out: list[NeighborEntry] = []
        for edge in self.model.edges:
            if edge.src == self.focus_id and edge.dest in nodes:
                out.append(NeighborEntry(edge, edge.dest, "out"))
        for edge in self.model.edges:
            if edge.dest == self.focus_id and edge.src in nodes:
                out.append(NeighborEntry(edge, edge.src, "in"))
        return out

    def cycle_neighbor(self, delta: int) -> bool:
        items = self.neighbors()
        if not items:
            return False
        n = len(items)
        if self.neighbor_index < 0:
            self.neighbor_index = 0 if delta > 0 else n - 1
        else:
            self.neighbor_index = (self.neighbor_index + delta) % n
        return True

    def toggle_kind(self) -> bool:
        if self.neighbor_index < 0 or not self.neighbors():
            return False
        self.select_kind = "edge" if self.select_kind == "node" else "node"
        return True

    def current_neighbor_id(self) -> int | None:
        items = self.neighbors()
        if self.neighbor_index < 0 or self.neighbor_index >= len(items):
            return None
        return items[self.neighbor_index].other_id

    def current_edge(self) -> GraphEdge | None:
        items = self.neighbors()
        if self.neighbor_index < 0 or self.neighbor_index >= len(items):
            return None
        return items[self.neighbor_index].edge

    def hop(self) -> bool:
        other = self.current_neighbor_id()
        if other is None or self.focus_id is None:
            return False
        # Truncate forward history, then push.
        self.jump_list = self.jump_list[: self.jump_index + 1]
        self.jump_list.append(other)
        self.jump_index = len(self.jump_list) - 1
        self.focus_id = other
        self.neighbor_index = -1
        self.select_kind = "node"
        return True

    def jump_back(self) -> bool:
        if self.jump_index <= 0:
            return False
        self.jump_index -= 1
        self.focus_id = self.jump_list[self.jump_index]
        self.neighbor_index = -1
        self.select_kind = "node"
        return True

    def jump_forward(self) -> bool:
        if self.jump_index < 0 or self.jump_index >= len(self.jump_list) - 1:
            return False
        self.jump_index += 1
        self.focus_id = self.jump_list[self.jump_index]
        self.neighbor_index = -1
        self.select_kind = "node"
        return True

    def focus_node(self) -> GraphNode | None:
        if self.model is None or self.focus_id is None:
            return None
        for node in self.model.nodes:
            if node.id == self.focus_id:
                return node
        return None

    def _clamp_neighbor(self) -> None:
        items = self.neighbors()
        if not items:
            self.neighbor_index = -1
            return
        if self.neighbor_index >= len(items):
            self.neighbor_index = len(items) - 1
