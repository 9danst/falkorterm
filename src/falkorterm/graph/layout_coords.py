from __future__ import annotations

import math
from collections import defaultdict, deque

from falkorterm.graph.colors import EMPTY_MESSAGE
from falkorterm.graph.extract import edge_key
from falkorterm.graph.models import (
    EdgePose,
    GraphEdge,
    GraphGeometry,
    GraphNode,
    GraphViewModel,
    NodePose,
)

DEFAULT_NODE_RADIUS = 1.3
DEFAULT_MARGIN = 2.0


def _assign_layers(
    nodes: dict[int, GraphNode], edges: tuple[GraphEdge, ...]
) -> dict[int, int]:
    """Longest-path layering; cycles broken via DFS feedback-arc set."""
    if not nodes:
        return {}

    outgoing: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        if edge.src in nodes and edge.dest in nodes and edge.src != edge.dest:
            outgoing[edge.src].append(edge.dest)

    back_edges = _feedback_arc_edges(nodes, outgoing)
    ranking_out: dict[int, list[int]] = defaultdict(list)
    indegree: dict[int, int] = {nid: 0 for nid in nodes}
    for edge in edges:
        if edge.src not in nodes or edge.dest not in nodes:
            continue
        if edge.src == edge.dest or (edge.src, edge.dest) in back_edges:
            continue
        ranking_out[edge.src].append(edge.dest)
        indegree[edge.dest] += 1

    indegree_work = dict(indegree)
    queue: deque[int] = deque(sorted(nid for nid, d in indegree_work.items() if d == 0))
    topo: list[int] = []
    while queue:
        cur = queue.popleft()
        topo.append(cur)
        for nxt in ranking_out.get(cur, []):
            indegree_work[nxt] -= 1
            if indegree_work[nxt] == 0:
                queue.append(nxt)

    layer: dict[int, int] = {nid: 0 for nid in nodes}
    for cur in topo:
        for nxt in ranking_out.get(cur, []):
            layer[nxt] = max(layer[nxt], layer[cur] + 1)

    seen = set(topo)
    leftovers = [nid for nid in sorted(nodes) if nid not in seen]
    if leftovers:
        bfs: deque[int] = deque(sorted(nid for nid, d in indegree.items() if d == 0))
        if not bfs:
            bfs.append(min(nodes))
        while bfs:
            cur = bfs.popleft()
            if cur not in layer:
                layer[cur] = 0
            for nxt in outgoing.get(cur, []):
                if nxt in layer and nxt in seen:
                    continue
                if nxt not in layer or layer[nxt] < layer[cur] + 1:
                    layer[nxt] = layer[cur] + 1
                    bfs.append(nxt)
        for nid in nodes:
            layer.setdefault(nid, 0)
    return layer


def _feedback_arc_edges(
    nodes: dict[int, GraphNode],
    outgoing: dict[int, list[int]],
) -> set[tuple[int, int]]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in nodes}
    back: set[tuple[int, int]] = set()

    def visit(u: int) -> None:
        color[u] = GRAY
        for v in outgoing.get(u, []):
            if color[v] == GRAY:
                back.add((u, v))
            elif color[v] == WHITE:
                visit(v)
        color[u] = BLACK

    outdeg = {nid: len(outgoing.get(nid, [])) for nid in nodes}
    for nid in sorted(nodes, key=lambda n: (-outdeg[n], n)):
        if color[nid] == WHITE:
            visit(nid)
    return back


def _assign_ego_layers(
    nodes: dict[int, GraphNode],
    edges: tuple[GraphEdge, ...],
    focus_id: int,
) -> dict[int, int]:
    """BFS hop distance from focus using undirected adjacency."""
    if focus_id not in nodes:
        return _assign_layers(nodes, edges)

    adj: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        if edge.src not in nodes or edge.dest not in nodes:
            continue
        if edge.src == edge.dest:
            continue
        adj[edge.src].append(edge.dest)
        adj[edge.dest].append(edge.src)

    layer: dict[int, int] = {focus_id: 0}
    queue: deque[int] = deque([focus_id])
    while queue:
        cur = queue.popleft()
        for nxt in sorted(adj.get(cur, [])):
            if nxt in layer:
                continue
            layer[nxt] = layer[cur] + 1
            queue.append(nxt)

    unreachable = [nid for nid in sorted(nodes) if nid not in layer]
    if unreachable:
        orphan_layer = (max(layer.values()) if layer else 0) + 1
        for nid in unreachable:
            layer[nid] = orphan_layer
    return layer


def _node_color_key(node: GraphNode) -> str | None:
    return node.labels[0] if node.labels else None


def _place_layered(
    nodes: dict[int, GraphNode],
    layers: dict[int, int],
) -> dict[int, tuple[float, float]]:
    by_layer: dict[int, list[int]] = defaultdict(list)
    for nid, ly in layers.items():
        by_layer[ly].append(nid)
    for ly in by_layer:
        by_layer[ly].sort()

    layer_gap = 6.0
    node_gap = 4.0
    positions: dict[int, tuple[float, float]] = {}
    for ly in sorted(by_layer):
        ids = by_layer[ly]
        n = len(ids)
        for i, nid in enumerate(ids):
            y = (i - (n - 1) / 2.0) * node_gap
            positions[nid] = (ly * layer_gap, y)
    return positions


def _place_ego(
    nodes: dict[int, GraphNode],
    layers: dict[int, int],
    focus_id: int,
) -> dict[int, tuple[float, float]]:
    by_layer: dict[int, list[int]] = defaultdict(list)
    for nid, ly in layers.items():
        by_layer[ly].append(nid)
    for ly in by_layer:
        by_layer[ly].sort()

    ring_gap = 5.0
    positions: dict[int, tuple[float, float]] = {}
    for ly in sorted(by_layer):
        ids = by_layer[ly]
        if ly == 0 and focus_id in ids:
            positions[focus_id] = (0.0, 0.0)
            ids = [n for n in ids if n != focus_id]
            if not ids:
                continue
        n = len(ids)
        radius = max(ring_gap, ly * ring_gap)
        for i, nid in enumerate(ids):
            angle = (2.0 * math.pi * i) / n - math.pi / 2.0
            positions[nid] = (radius * math.cos(angle), radius * math.sin(angle))
    return positions


def _auto_fit(
    raw: dict[int, tuple[float, float]],
    *,
    width: int,
    height: int,
    radius: float,
    margin: float,
) -> dict[int, tuple[float, float]]:
    if not raw:
        return {}
    xs = [p[0] for p in raw.values()]
    ys = [p[1] for p in raw.values()]
    min_x, max_x = min(xs) - radius, max(xs) + radius
    min_y, max_y = min(ys) - radius, max(ys) + radius
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    avail_w = max(width - 2 * margin, 1.0)
    avail_h = max(height - 2 * margin, 1.0)
    scale = min(avail_w / span_x, avail_h / span_y)
    # Center of raw bbox → center of widget
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    tx = width / 2.0
    ty = height / 2.0
    fitted: dict[int, tuple[float, float]] = {}
    for nid, (x, y) in raw.items():
        fitted[nid] = (tx + (x - cx) * scale, ty + (y - cy) * scale)
    return fitted


def layout_coords(
    model: GraphViewModel,
    *,
    width: int,
    height: int,
    focus_id: int | None = None,
    node_radius: float = DEFAULT_NODE_RADIUS,
    margin: float = DEFAULT_MARGIN,
) -> GraphGeometry:
    """Compute continuous node/edge poses for the hires canvas."""
    width = max(int(width), 1)
    height = max(int(height), 1)
    nodes = {n.id: n for n in model.nodes}
    if not nodes:
        return GraphGeometry(
            nodes=(),
            edges=(),
            node_order=(),
            edge_order=(),
            width=width,
            height=height,
        )

    ego = focus_id is not None and focus_id in nodes
    layers = (
        _assign_ego_layers(nodes, model.edges, focus_id)
        if ego
        else _assign_layers(nodes, model.edges)
    )
    raw = (
        _place_ego(nodes, layers, focus_id)  # type: ignore[arg-type]
        if ego
        else _place_layered(nodes, layers)
    )
    fitted = _auto_fit(
        raw, width=width, height=height, radius=node_radius, margin=margin
    )

    node_order = tuple(n.id for n in model.nodes)
    poses: list[NodePose] = []
    for nid in node_order:
        node = nodes[nid]
        x, y = fitted[nid]
        poses.append(
            NodePose(
                id=nid,
                x=x,
                y=y,
                r=node_radius,
                color_key=_node_color_key(node),
            )
        )
    by_id = {p.id: p for p in poses}

    edge_order: list[object] = []
    edge_poses: list[EdgePose] = []
    for edge in model.edges:
        if edge.src not in by_id or edge.dest not in by_id:
            continue
        key = edge_key(edge)
        edge_order.append(key)
        a, b = by_id[edge.src], by_id[edge.dest]
        edge_poses.append(
            EdgePose(
                key=key,
                x0=a.x,
                y0=a.y,
                x1=b.x,
                y1=b.y,
                type=edge.type,
            )
        )

    return GraphGeometry(
        nodes=tuple(poses),
        edges=tuple(edge_poses),
        node_order=node_order,
        edge_order=tuple(edge_order),
        width=width,
        height=height,
    )


def format_session_text(model: GraphViewModel) -> str:
    """Plain-text session summary for clipboard copy."""
    if not model.nodes:
        return EMPTY_MESSAGE
    lines: list[str] = []
    connected: set[int] = set()
    for edge in model.edges:
        lines.append(f"({edge.src})-[:{edge.type}]->({edge.dest})")
        connected.add(edge.src)
        connected.add(edge.dest)
    for node in model.nodes:
        if node.id not in connected:
            lines.append(node.display)
    return "\n".join(lines)
