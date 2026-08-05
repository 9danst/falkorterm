from __future__ import annotations

from rich.text import Text

from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.models import GraphEdge, GraphNode
from falkorterm.graph.render_text import node_caption
from falkorterm.graph.session import NeighborEntry, SurfSession

_PROP_KEYS = ("name", "title", "code", "iata", "label")
_REL_WIDTH = 10
_CAPTION_WIDTH = 20

_HINT_FOCUS = "j/k neighbor · Enter inspect · x expand · g cycle"
_HINT_NODE = "l hop · Tab edge · Enter inspect · h back · L forward"
_HINT_EDGE = "Tab node · Enter inspect edge · l hop · h back"


def surf_hint(session: SurfSession) -> str:
    """Contextual footer / Results subtitle hint for Surf."""
    if session.model is None or session.focus_id is None:
        return _HINT_FOCUS
    if session.neighbor_index < 0 or not session.neighbors():
        return _HINT_FOCUS
    if session.select_kind == "edge":
        return _HINT_EDGE
    return _HINT_NODE


def render_surf(session: SurfSession) -> Text:
    """Render Surf's dense one-hop inspector."""
    model = session.model
    focus = session.focus_node()
    if model is None or not model.nodes or focus is None:
        return Text(EMPTY_MESSAGE)

    nodes = {node.id: node for node in model.nodes}
    neighbors = session.neighbors()
    outbound = [(i, entry) for i, entry in enumerate(neighbors) if entry.direction == "out"]
    inbound = [(i, entry) for i, entry in enumerate(neighbors) if entry.direction == "in"]
    out = Text()

    out.append("trail: ", style="dim")
    _append_trail(out, session, nodes)
    out.append("\n")

    depth = session.jump_index + 1 if session.jump_index >= 0 else 0
    jump_n = len(session.jump_list)
    jump_i = session.jump_index + 1 if session.jump_index >= 0 else 0
    out.append(f"depth {depth} · jump {jump_i}/{jump_n}", style="dim")
    out.append("\n")

    header = f"session: {len(model.nodes)} nodes · {len(model.edges)} edges"
    if model.truncated:
        header += " · truncated"
    out.append(header, style="dim")
    out.append("\n\n")

    kind = "EDGE" if session.select_kind == "edge" and session.neighbor_index >= 0 else "NODE"
    _append_focus_box(
        out,
        focus,
        out_count=len(outbound),
        in_count=len(inbound),
        kind=kind,
    )
    out.append("\n")

    _append_neighbor_section(out, "OUT", outbound, nodes, session)
    out.append("\n")
    _append_neighbor_section(out, "IN", inbound, nodes, session)

    if session.neighbor_index >= 0:
        out.append("\n")
        _append_selected_panel(out, session, nodes)

    out.append("\n")
    out.append(surf_hint(session), style="dim")
    return out


def _append_trail(
    out: Text,
    session: SurfSession,
    nodes: dict[int, GraphNode],
) -> None:
    ids = (
        session.jump_list[: session.jump_index + 1]
        if session.jump_index >= 0
        else list(session.jump_list)
    )
    ids = [node_id for node_id in ids if node_id in nodes]
    truncated = len(ids) > 6
    ids = ids[-6:]
    if not ids:
        focus = session.focus_node()
        if focus is not None:
            out.append(_display_caption(focus), style=_caption_style(focus, bold=True))
        return

    if truncated:
        out.append("…", style="dim")
        out.append(" → ", style="dim")

    last = len(ids) - 1
    for index, node_id in enumerate(ids):
        node = nodes[node_id]
        if index:
            edge = _edge_between(session, ids[index - 1], node_id)
            if edge is None:
                out.append(" → ", style="dim")
            else:
                out.append(" → ", style="dim")
                out.append(f"[:{edge.type}]", style="dim")
                out.append(" → ", style="dim")
        if index == last:
            out.append(_display_caption(node), style=_caption_style(node, bold=True))
        else:
            out.append(_display_caption(node), style="dim")


def _append_focus_box(
    out: Text,
    focus: GraphNode,
    *,
    out_count: int,
    in_count: int,
    kind: str,
) -> None:
    caption = _display_caption(focus)
    meta = _node_meta(focus)
    title = f"{caption}{meta}"
    props_line = " · ".join(_prop_pairs(focus))
    header = f" FOCUS · OUT {out_count} · IN {in_count} · {kind} "
    inner_lines = [title]
    if props_line:
        inner_lines.append(props_line)
    width = max(len(header), max(len(line) for line in inner_lines)) + 2

    top = f"┏{header}{'━' * max(0, width - len(header) - 1)}┓"
    out.append(top + "\n", style="bold")

    out.append("┃", style="bold")
    out.append(f" {caption}", style=_caption_style(focus, bold=True))
    out.append(meta, style="dim")
    pad = (width - 2) - len(title)
    out.append((" " * pad) + " ", style="dim")
    out.append("┃\n", style="bold")

    if props_line:
        padded = f" {props_line:<{width - 2}} "
        out.append("┃", style="bold")
        out.append(padded, style="dim")
        out.append("┃\n", style="bold")

    out.append("┗" + ("━" * width) + "┛\n", style="bold")


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
        cursor = "▸ " if selected else "  "
        if selected and session.select_kind == "edge":
            rel_raw = f"«{entry.edge.type}»"
            rel_style = "bold"
        else:
            rel_raw = f"[:{entry.edge.type}]"
            rel_style = "dim"
        rel = f"{rel_raw:<{_REL_WIDTH}}"
        arrow = "→" if entry.direction == "out" else "←"
        caption = _truncate(_display_caption(other), _CAPTION_WIDTH)
        labels = f":{':'.join(other.labels)}" if other.labels else ""
        prop = _first_prop(other)

        out.append(cursor, style="bold" if selected else "")
        out.append(rel, style=rel_style)
        out.append(f" {arrow} ", style="dim")
        if selected:
            out.append(caption, style=_caption_style(other, bold=True))
        else:
            out.append(caption)
        if labels:
            out.append(f" {labels}", style="dim")
        if prop:
            out.append(f"  {prop}", style="dim")
        out.append("\n")


def _append_selected_panel(
    out: Text,
    session: SurfSession,
    nodes: dict[int, GraphNode],
) -> None:
    edge = session.current_edge()
    other_id = session.current_neighbor_id()
    if edge is None or other_id is None:
        return
    other = nodes.get(other_id)
    if other is None:
        return

    caption = _display_caption(other)
    meta = _node_meta(other)
    out.append("── selected ──────────────────────────\n", style="dim")
    out.append(caption, style=_caption_style(other, bold=True))
    out.append(meta + "\n", style="dim")
    via_style = "bold" if session.select_kind == "edge" else "dim"
    out.append(f"via [:{edge.type}]", style=via_style)
    out.append("\n")
    edge_props = _prop_pairs_from_mapping(edge.properties)
    if edge_props:
        out.append(" · ".join(edge_props) + "\n", style="dim")
    else:
        node_props = _prop_pairs(other)
        if node_props:
            out.append(" · ".join(node_props) + "\n", style="dim")


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
    return _prop_pairs_from_mapping(node.properties)


def _prop_pairs_from_mapping(props: dict[str, object]) -> list[str]:
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


def _first_prop(node: GraphNode) -> str | None:
    pairs = _prop_pairs(node)
    return pairs[0] if pairs else None


def _node_meta(node: GraphNode) -> str:
    labels = f" :{':'.join(node.labels)}" if node.labels else ""
    return f"{labels} id={node.id}"


def _display_caption(node: GraphNode) -> str:
    return node.display or node_caption(node, max_len=32)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _caption_style(node: GraphNode, *, bold: bool = False) -> str:
    """Palette color for primary display names only."""
    style = color_for(node.labels[0]) if node.labels else "white"
    return f"bold {style}" if bold else style
