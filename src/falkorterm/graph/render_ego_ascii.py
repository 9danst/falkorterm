from __future__ import annotations

from rich.text import Text

from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_text import node_caption

MAX_NEIGHBORS = 8


def _box(node: GraphNode, *, selected: bool = False) -> list[str]:
    caption = node_caption(node, max_len=28)
    width = max(len(caption), 8)
    h, v = ("═", "║") if selected else ("─", "│")
    tl, tr, bl, br = (
        ("╔", "╗", "╚", "╝") if selected else ("┌", "┐", "└", "┘")
    )
    return [
        f"{tl}{h * (width + 2)}{tr}",
        f"{v} {caption:<{width}} {v}",
        f"{bl}{h * (width + 2)}{br}",
    ]


def ego_neighbors(
    model: GraphViewModel, focus_id: int
) -> list[tuple[GraphEdge, GraphNode, str]]:
    """Return (edge, other_node, direction) for 1-hop around focus."""
    nodes = {n.id: n for n in model.nodes}
    if focus_id not in nodes:
        return []
    out: list[tuple[GraphEdge, GraphNode, str]] = []
    for edge in model.edges:
        if edge.src == focus_id and edge.dest in nodes and edge.dest != focus_id:
            out.append((edge, nodes[edge.dest], "out"))
        elif edge.dest == focus_id and edge.src in nodes and edge.src != focus_id:
            out.append((edge, nodes[edge.src], "in"))
    return out


def render_ego_ascii(
    model: GraphViewModel,
    focus_id: int | None,
    *,
    selected_neighbor_id: int | None = None,
    max_neighbors: int = MAX_NEIGHBORS,
) -> Text:
    """ASCII ego map: focus box + up to max_neighbors 1-hop neighbors."""
    if not model.nodes:
        return Text(EMPTY_MESSAGE)

    nodes = {n.id: n for n in model.nodes}
    if focus_id is None or focus_id not in nodes:
        focus_id = model.nodes[0].id

    focus = nodes[focus_id]
    neighbors = ego_neighbors(model, focus_id)
    shown = neighbors[:max_neighbors]
    truncated = len(neighbors) - len(shown)

    out = Text()
    header = f"ego id={focus_id} · {len(neighbors)} neighbor(s)"
    if truncated > 0:
        header += f" · +{truncated} more"
    out.append(header + "\n\n", style="dim")

    # Neighbor row above (first half) — simple vertical stack under focus is clearer.
    focus_style = color_for(focus.labels[0]) if focus.labels else "bold white"
    for line in _box(focus, selected=True):
        out.append(line + "\n", style=focus_style)
    out.append("\n")

    if not shown:
        out.append("  (no neighbors in session)\n", style="dim")
    else:
        out.append("Neighbors\n", style="bold")
        for edge, other, direction in shown:
            mark = "» " if other.id == selected_neighbor_id else "  "
            rel = f"[:{edge.type}]"
            rel_style = color_for(edge.type)
            other_style = color_for(other.labels[0]) if other.labels else "white"
            if other.id == selected_neighbor_id:
                other_style = f"bold {other_style}"
            out.append(mark)
            if direction == "out":
                out.append("- ")
                out.append(rel, style=rel_style)
                out.append(" -> ")
            else:
                out.append("<- ")
                out.append(rel, style=rel_style)
                out.append(" - ")
            out.append(node_caption(other, max_len=40), style=other_style)
            out.append("\n")
        if truncated > 0:
            out.append(f"  … +{truncated} more\n", style="dim")

    out.append("\n")
    out.append("j/k neighbor · Enter inspect · x expand · h/l focus stack", style="dim")
    return out
