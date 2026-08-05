from __future__ import annotations

from falkorterm.graph.extract import edge_key
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


def _node_richness(node: GraphNode) -> tuple[int, int, int]:
    """Higher means prefer this node when upgrading a placeholder."""
    return (len(node.labels), len(node.properties), len(node.display))


def _prefer_node(current: GraphNode, candidate: GraphNode) -> GraphNode:
    if _node_richness(candidate) > _node_richness(current):
        return candidate
    return current


def merge_graphs(
    base: GraphViewModel,
    incoming: GraphViewModel,
    *,
    max_nodes: int = 50,
    max_edges: int = 80,
) -> GraphViewModel:
    """Union two graph models: base order first, then new nodes/edges from incoming.

    Duplicate nodes (by id) and edges (by edge_key) are skipped, except nodes may
    be upgraded when the incoming copy is richer (labels/props). Caps apply after
    the union; truncated/total_* reflect the uncapped union sizes.
    """
    nodes: dict[int, GraphNode] = {}
    node_order: list[int] = []
    edges: dict[object, GraphEdge] = {}
    edge_order: list[object] = []

    def add_node(node: GraphNode) -> None:
        existing = nodes.get(node.id)
        if existing is None:
            nodes[node.id] = node
            node_order.append(node.id)
            return
        nodes[node.id] = _prefer_node(existing, node)

    def add_edge(edge: GraphEdge) -> None:
        key = edge_key(edge)
        if key in edges:
            return
        edges[key] = edge
        edge_order.append(key)

    for node in base.nodes:
        add_node(node)
    for edge in base.edges:
        add_edge(edge)
    for node in incoming.nodes:
        add_node(node)
    for edge in incoming.edges:
        add_edge(edge)

    total_nodes = len(node_order)
    total_edges = len(edge_order)
    kept_node_ids = node_order[:max_nodes]
    kept_set = set(kept_node_ids)
    kept_edge_keys: list[object] = []
    for key in edge_order:
        if len(kept_edge_keys) >= max_edges:
            break
        edge = edges[key]
        if edge.src in kept_set and edge.dest in kept_set:
            kept_edge_keys.append(key)

    truncated = total_nodes > len(kept_node_ids) or total_edges > len(kept_edge_keys)

    return GraphViewModel(
        nodes=tuple(nodes[nid] for nid in kept_node_ids),
        edges=tuple(edges[k] for k in kept_edge_keys),
        truncated=truncated or base.truncated or incoming.truncated,
        total_nodes=total_nodes,
        total_edges=total_edges,
    )
