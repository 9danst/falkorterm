from __future__ import annotations

from rich.text import Text

from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.models import GraphEdge, GraphNode
from falkorterm.graph.render_text import node_caption
from falkorterm.graph.session import NeighborEntry, SurfSession

_PROP_KEYS = ("name", "title", "code", "iata", "label")
_HINT = "j/k · l hop · h/Ctrl+o back · L forward · Tab edge · x expand · g cycle"


def render_surf(session: SurfSession) -> Text:
    """Render Surf's dense one-hop inspector."""
    model = session.model
    focus = session.focus_node()
    if model is None or not model.nodes or focus is None:
        return Text(EMPTY_MESSAGE)

    nodes = {node.id: node for node in model.nodes}
    neighbors = session.neighbors()
    out = Text()

    out.append("trail: ", style="dim")
    _append_trail(out, session, nodes)
    out.append("\n")

    header = f"session: {len(model.nodes)} nodes · {len(model.edges)} edges"
    if model.truncated:
        header += " · truncated"
    out.append(header, style="dim")
    out.append("\n\n")

    focus_style = _node_style(focus, bold=True)
    out.append("● FOCUS  ", style="bold")
    out.append(_node_title(focus), style=focus_style)
    out.append("\n")
    props = _prop_pairs(focus)
    if props:
        out.append("  " + " · ".join(props) + "\n", style=focus_style)
    out.append("\n")

    outbound = [(i, entry) for i, entry in enumerate(neighbors) if entry.direction == "out"]
    inbound = [(i, entry) for i, entry in enumerate(neighbors) if entry.direction == "in"]
    _append_neighbor_section(out, "OUT", outbound, nodes, session)
    out.append("\n")
    _append_neighbor_section(out, "IN", inbound, nodes, session)

    out.append("\n")
    out.append(_HINT, style="dim")
    return out


def _append_trail(
    out: Text,
    session: SurfSession,
    nodes: dict[int, GraphNode],
) -> None:
    ids = session.jump_list[: session.jump_index + 1] if session.jump_index >= 0 else session.jump_list
    ids = [node_id for node_id in ids if node_id in nodes][-6:]
    if not ids:
        focus = session.focus_node()
        if focus is not None:
            out.append(_display_caption(focus), style=_node_style(focus))
        return

    for index, node_id in enumerate(ids):
        node = nodes[node_id]
        if index:
            edge = _edge_between(session, ids[index - 1], node_id)
            if edge is None:
                out.append(" → ", style="dim")
            else:
                out.append(" → ", style="dim")
                out.append(f"[:{edge.type}]", style=color_for(edge.type))
                out.append(" → ", style="dim")
        out.append(_display_caption(node), style=_node_style(node))


def _append_neighbor_section(
    out: Text,
    title: str,
    entries: list[tuple[int, NeighborEntry]],
    nodes: dict[int, GraphNode],
    session: SurfSession,
) -> None:
    out.append(f"{title} {len(entries)}\n", style="bold")
    if not entries:
        out.append("  (none)\n", style="dim")
        return

    for index, entry in entries:
        other = nodes.get(entry.other_id)
        if other is None:
            continue
        selected = index == session.neighbor_index
        out.append("▸ " if selected else "  ", style="bold" if selected else "")
        rel = f"«{entry.edge.type}»" if selected and session.select_kind == "edge" else f"[:{entry.edge.type}]"
        rel_style = f"bold {color_for(entry.edge.type)}" if selected else color_for(entry.edge.type)
        out.append(rel, style=rel_style)
        arrow = " → " if entry.direction == "out" else " ← "
        out.append(arrow, style="dim")
        out.append(_node_title(other), style=_node_style(other))
        out.append("\n")


def _edge_between(session: SurfSession, src_id: int, dest_id: int) -> GraphEdge | None:
    if session.model is None:
        return None
    for edge in session.model.edges:
        if edge.src == src_id and edge.dest == dest_id:
            return edge
    for edge in session.model.edges:
        if edge.dest == src_id and edge.src == dest_id:
            return edge
    return None


def _prop_pairs(node: GraphNode) -> list[str]:
    props = node.properties
    seen: set[str] = set()
    pairs: list[str] = []
    for key in _PROP_KEYS:
        if key in props and props[key] is not None:
            pairs.append(f"{key}={props[key]}")
            seen.add(key)
            if len(pairs) == 3:
                return pairs
    for key, value in props.items():
        if key in seen or value is None:
            continue
        pairs.append(f"{key}={value}")
        if len(pairs) == 3:
            return pairs
    return pairs


def _node_title(node: GraphNode) -> str:
    labels = f" :{':'.join(node.labels)}" if node.labels else ""
    return f"{_display_caption(node)}{labels} id={node.id}"


def _display_caption(node: GraphNode) -> str:
    return node.display or node_caption(node, max_len=32)


def _node_style(node: GraphNode, *, bold: bool = False) -> str:
    style = color_for(node.labels[0]) if node.labels else "white"
    return f"bold {style}" if bold else style
