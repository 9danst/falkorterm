from __future__ import annotations

from rich.text import Text

from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.extract import edge_key
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel

_PROP_KEYS = ("name", "title", "code", "iata", "label", "id")
_MAX_LINE = 72


def _prop_snippet(node: GraphNode) -> str | None:
    props = node.properties
    for key in ("name", "title", "code", "iata", "label"):
        if key in props and props[key] is not None:
            return f"{key}={props[key]}"
    for key, value in props.items():
        if key in _PROP_KEYS or value is None:
            continue
        return f"{key}={value}"
    return None


def node_caption(node: GraphNode, *, max_len: int = 48) -> str:
    if node.labels:
        head = f":{':'.join(node.labels)} id={node.id}"
    else:
        head = f"id={node.id}"
    prop = _prop_snippet(node)
    text = f"{head} {prop}" if prop else head
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _truncate(text: str, max_len: int = _MAX_LINE) -> str:
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _box_lines(node: GraphNode, *, selected: bool) -> list[str]:
    caption = node_caption(node, max_len=40)
    prop = _prop_snippet(node)
    lines_inner = [caption]
    if prop and prop not in caption:
        lines_inner.append(prop)
    width = max(len(s) for s in lines_inner)
    h, v = ("═", "║") if selected else ("─", "│")
    tl, tr, bl, br = (
        ("╔", "╗", "╚", "╝") if selected else ("┌", "┐", "└", "┘")
    )
    out = [f"{tl}{h * (width + 2)}{tr}"]
    for part in lines_inner:
        out.append(f"{v} {part:<{width}} {v}")
    out.append(f"{bl}{h * (width + 2)}{br}")
    return out


def render_graph_text(
    model: GraphViewModel,
    *,
    selected_id: int | None = None,
    selected_edge_key: object | None = None,
    focus_id: int | None = None,
    select_kind: str = "node",
) -> Text:
    """Readable neighborhood / edge-list view (not a pixel canvas)."""
    if not model.nodes:
        return Text(EMPTY_MESSAGE)

    nodes = {n.id: n for n in model.nodes}
    out = Text()

    header = f"{len(model.nodes)} nodes · {len(model.edges)} edges"
    if model.truncated:
        header += " · truncated"
    if focus_id is not None and focus_id in nodes:
        header += f" · ego id={focus_id}"
    header += f" · mode={'edge' if select_kind == 'edge' else 'node'}"
    out.append(header, style="dim")
    out.append("\n\n")

    if select_kind == "edge":
        _append_edge_list(out, model, nodes, selected_edge_key=selected_edge_key)
        return out

    hub_id = selected_id if selected_id in nodes else next(iter(nodes))
    hub = nodes[hub_id]
    label_style = color_for(hub.labels[0]) if hub.labels else "white"

    out.append("Selected\n", style="bold")
    for line in _box_lines(hub, selected=True):
        out.append(line + "\n", style=label_style)
    out.append("\n")

    outbound = [
        e for e in model.edges if e.src == hub_id and e.dest in nodes
    ]
    inbound = [
        e for e in model.edges if e.dest == hub_id and e.src in nodes
    ]

    out.append(f"Outbound ({len(outbound)})\n", style="bold")
    if not outbound:
        out.append("  (none)\n", style="dim")
    else:
        for edge in outbound:
            _append_neighbor_edge(
                out,
                edge,
                other=nodes[edge.dest],
                direction="out",
                selected=selected_edge_key == edge_key(edge),
            )

    out.append("\n")
    out.append(f"Inbound ({len(inbound)})\n", style="bold")
    if not inbound:
        out.append("  (none)\n", style="dim")
    else:
        for edge in inbound:
            _append_neighbor_edge(
                out,
                edge,
                other=nodes[edge.src],
                direction="in",
                selected=selected_edge_key == edge_key(edge),
            )

    adjacent = {hub_id}
    for edge in outbound:
        adjacent.add(edge.dest)
    for edge in inbound:
        adjacent.add(edge.src)
    others = [n for n in model.nodes if n.id not in adjacent]
    if others:
        out.append("\n")
        out.append(f"Other nodes ({len(others)})\n", style="bold dim")
        for node in others[:20]:
            style = color_for(node.labels[0]) if node.labels else "dim"
            mark = "» " if node.id == selected_id else "  "
            out.append(f"{mark}{node_caption(node)}\n", style=style)
        if len(others) > 20:
            out.append(f"  … +{len(others) - 20} more\n", style="dim")

    out.append("\n")
    out.append("j/k select · Tab edges · Enter inspect · x expand", style="dim")
    return out


def _append_neighbor_edge(
    out: Text,
    edge: GraphEdge,
    *,
    other: GraphNode,
    direction: str,
    selected: bool,
) -> None:
    other_style = color_for(other.labels[0]) if other.labels else "white"
    rel_style = f"bold {color_for(edge.type)}" if selected else color_for(edge.type)
    prefix = "» " if selected else "  "
    rel = f"«{edge.type}»" if selected else f"[:{edge.type}]"
    cap = _truncate(node_caption(other, max_len=40))

    out.append(prefix, style="bold" if selected else "")
    if direction == "out":
        out.append("- ")
        out.append(rel, style=rel_style)
        out.append(" -> ")
    else:
        out.append("<- ")
        out.append(rel, style=rel_style)
        out.append(" - ")
    out.append(cap, style=other_style)
    out.append("\n")


def _append_edge_list(
    out: Text,
    model: GraphViewModel,
    nodes: dict[int, GraphNode],
    *,
    selected_edge_key: object | None,
) -> None:
    out.append("All edges\n", style="bold")
    if not model.edges:
        out.append("  (none)\n", style="dim")
        return
    for edge in model.edges:
        key = edge_key(edge)
        selected = key == selected_edge_key
        prefix = "» " if selected else "  "
        src = nodes.get(edge.src)
        dest = nodes.get(edge.dest)
        src_cap = node_caption(src, max_len=28) if src else f"id={edge.src}"
        dest_cap = node_caption(dest, max_len=28) if dest else f"id={edge.dest}"
        rel = f"«{edge.type}»" if selected else f"[:{edge.type}]"
        out.append(prefix, style="bold" if selected else "")
        out.append(
            f"({src_cap})",
            style=color_for(src.labels[0]) if src and src.labels else "",
        )
        out.append(f"-{rel}->", style=color_for(edge.type))
        out.append(
            f"({dest_cap})",
            style=color_for(dest.labels[0]) if dest and dest.labels else "",
        )
        out.append("\n")
    out.append("\n")
    out.append("j/k select · Tab nodes · Enter inspect", style="dim")
