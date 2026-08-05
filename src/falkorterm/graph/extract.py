from __future__ import annotations

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _props(detail: dict[str, object]) -> dict[str, object]:
    raw = detail.get("properties") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def _labels(detail: dict[str, object]) -> tuple[str, ...]:
    raw = detail.get("labels") or []
    if isinstance(raw, (list, tuple)):
        return tuple(str(x) for x in raw)
    return ()


def _node_display(node_id: int, labels: tuple[str, ...], fallback: str = "") -> str:
    if fallback:
        return fallback
    if labels:
        return f"(:{':'.join(labels)} id={node_id})"
    return f"(node id={node_id})"


def _node_from_detail(detail: dict[str, object], display: str = "") -> GraphNode | None:
    node_id = _as_int(detail.get("id"))
    if node_id is None:
        return None
    labels = _labels(detail)
    return GraphNode(
        id=node_id,
        labels=labels,
        properties=_props(detail),
        display=_node_display(node_id, labels, display),
    )


def _edge_from_detail(
    detail: dict[str, object],
    *,
    default_src: int | None = None,
    default_dest: int | None = None,
) -> GraphEdge | None:
    src = _as_int(detail.get("src"))
    dest = _as_int(detail.get("dest"))
    if src is None:
        src = default_src
    if dest is None:
        dest = default_dest
    if src is None or dest is None:
        return None
    return GraphEdge(
        src=src,
        dest=dest,
        type=str(detail.get("type") or "REL"),
        id=_as_int(detail.get("id")),
        properties=_props(detail),
    )


def edge_key(edge: GraphEdge) -> object:
    """Stable dedupe key: relationship id when present, else (src, type, dest)."""
    if edge.id is not None:
        return ("id", edge.id)
    return ("triple", edge.src, edge.type, edge.dest)


# Back-compat alias for internal call sites.
_edge_key = edge_key


class _Accumulator:
    def __init__(self) -> None:
        self.nodes: dict[int, GraphNode] = {}
        self.edges: dict[object, GraphEdge] = {}
        self.node_order: list[int] = []
        self.edge_order: list[object] = []

    def add_node(self, node: GraphNode) -> None:
        if node.id in self.nodes:
            return
        self.nodes[node.id] = node
        self.node_order.append(node.id)

    def add_edge(self, edge: GraphEdge) -> None:
        key = _edge_key(edge)
        if key in self.edges:
            return
        self.edges[key] = edge
        self.edge_order.append(key)
        if edge.src not in self.nodes:
            self.add_node(
                GraphNode(
                    id=edge.src,
                    labels=(),
                    properties={},
                    display=_node_display(edge.src, ()),
                )
            )
        if edge.dest not in self.nodes:
            self.add_node(
                GraphNode(
                    id=edge.dest,
                    labels=(),
                    properties={},
                    display=_node_display(edge.dest, ()),
                )
            )

    def ingest_node_cell(self, cell: CellValue) -> None:
        if not cell.detail or cell.detail.get("kind") != "node":
            return
        node = _node_from_detail(cell.detail, cell.display)
        if node is not None:
            self.add_node(node)

    def ingest_edge_detail(
        self,
        detail: dict[str, object],
        *,
        default_src: int | None = None,
        default_dest: int | None = None,
    ) -> None:
        edge = _edge_from_detail(
            detail, default_src=default_src, default_dest=default_dest
        )
        if edge is not None:
            self.add_edge(edge)

    def ingest_path_cell(self, cell: CellValue) -> None:
        detail = cell.detail
        if not detail or detail.get("kind") != "path":
            return
        raw_nodes = detail.get("nodes") or []
        if isinstance(raw_nodes, list):
            for item in raw_nodes:
                if isinstance(item, dict):
                    node = _node_from_detail(item)
                    if node is not None:
                        self.add_node(node)
        raw_edges = detail.get("edges") or []
        if isinstance(raw_edges, list):
            for item in raw_edges:
                if isinstance(item, dict):
                    self.ingest_edge_detail(item)


def extract_graph(
    result: QueryResult,
    *,
    max_nodes: int = 25,
    max_edges: int = 40,
) -> GraphViewModel:
    acc = _Accumulator()

    for row in result.rows:
        for cell in row:
            if cell.detail and cell.detail.get("kind") == "path":
                acc.ingest_path_cell(cell)

        i = 0
        while i + 2 < len(row):
            a, b, c = row[i], row[i + 1], row[i + 2]
            a_d, b_d, c_d = a.detail, b.detail, c.detail
            if (
                a_d
                and b_d
                and c_d
                and a_d.get("kind") == "node"
                and b_d.get("kind") == "edge"
                and c_d.get("kind") == "node"
            ):
                acc.ingest_node_cell(a)
                acc.ingest_node_cell(c)
                acc.ingest_edge_detail(
                    b_d,
                    default_src=_as_int(a_d.get("id")),
                    default_dest=_as_int(c_d.get("id")),
                )
                i += 2
                continue
            i += 1

        for cell in row:
            kind = cell.detail.get("kind") if cell.detail else None
            if kind == "node":
                acc.ingest_node_cell(cell)
            elif kind == "edge":
                acc.ingest_edge_detail(cell.detail)  # type: ignore[arg-type]

    total_nodes = len(acc.node_order)
    total_edges = len(acc.edge_order)
    kept_node_ids = acc.node_order[:max_nodes]
    kept_set = set(kept_node_ids)
    kept_edge_keys: list[object] = []
    for key in acc.edge_order:
        if len(kept_edge_keys) >= max_edges:
            break
        edge = acc.edges[key]
        if edge.src in kept_set and edge.dest in kept_set:
            kept_edge_keys.append(key)

    truncated = total_nodes > len(kept_node_ids) or total_edges > len(kept_edge_keys)

    return GraphViewModel(
        nodes=tuple(acc.nodes[nid] for nid in kept_node_ids),
        edges=tuple(acc.edges[k] for k in kept_edge_keys),
        truncated=truncated,
        total_nodes=total_nodes,
        total_edges=total_edges,
    )
