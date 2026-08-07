from __future__ import annotations

from collections import defaultdict, deque

from rich.text import Text

from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.display import GraphDisplayOptions, format_prop_line, props_for_node
from falkorterm.graph.models import AsciiCanvas, GraphEdge, GraphNode, GraphViewModel, Hitbox

NO_VISIBLE_MESSAGE = "No visible nodes — enable a label in display panel (p)"

_PROP_KEYS = ("name", "title", "id", "label")
_MAX_PROP_LEN = 16
_BOX_BORDER_CHARS = frozenset("┌┐└┘─│╔╗╚╝═║")

# Box-drawing merge when two pipe strokes meet.
_MERGE: dict[tuple[str, str], str] = {
    ("─", "│"): "┼",
    ("│", "─"): "┼",
    ("─", "─"): "─",
    ("│", "│"): "│",
    ("─", "▶"): "▶",
    ("│", "▶"): "▶",
    ("─", "▲"): "▲",
    ("│", "▲"): "▲",
    ("─", "▼"): "▼",
    ("│", "▼"): "▼",
    ("┌", "─"): "┌",
    ("┌", "│"): "┌",
    ("┐", "─"): "┐",
    ("┐", "│"): "┐",
    ("└", "─"): "└",
    ("└", "│"): "└",
    ("┘", "─"): "┘",
    ("┘", "│"): "┘",
    ("┬", "─"): "┬",
    ("┬", "│"): "┼",
    ("┴", "─"): "┴",
    ("┴", "│"): "┼",
    ("├", "│"): "├",
    ("├", "─"): "┼",
    ("┤", "│"): "┤",
    ("┤", "─"): "┼",
    ("┼", "─"): "┼",
    ("┼", "│"): "┼",
}


def _display_prop(node: GraphNode) -> str | None:
    props = node.properties
    for key in ("name", "title", "label"):
        if key in props and props[key] is not None:
            text = str(props[key]).replace("\n", " ")
            if len(text) > _MAX_PROP_LEN:
                return text[: _MAX_PROP_LEN - 1] + "…"
            return text
    for key, value in props.items():
        if key in _PROP_KEYS or value is None:
            continue
        text = str(value).replace("\n", " ")
        if len(text) > _MAX_PROP_LEN:
            return text[: _MAX_PROP_LEN - 1] + "…"
        return text
    return None


def _box_lines(
    node: GraphNode,
    selected: bool = False,
    *,
    display: GraphDisplayOptions | None = None,
) -> list[str]:
    label = f":{':'.join(node.labels)}" if node.labels else "node"
    inner_parts: list[str] = [label]
    if display is None or display.show_id:
        inner_parts.append(f"id={node.id}")
    if display is None:
        prop = _display_prop(node)
        if prop:
            inner_parts.append(prop)
    else:
        for key in props_for_node(node, display):
            value = node.properties.get(key)
            if value is not None:
                inner_parts.append(
                    format_prop_line(key, value, max_len=_MAX_PROP_LEN)
                )
    inner_w = max(*(len(p) for p in inner_parts), 8)
    h, v = ("═", "║") if selected else ("─", "│")
    tl, tr, bl, br = (
        ("╔", "╗", "╚", "╝") if selected else ("┌", "┐", "└", "┘")
    )
    lines = [tl + h * (inner_w + 2) + tr]
    for part in inner_parts:
        lines.append(v + f" {part:<{inner_w}} " + v)
    lines.append(bl + h * (inner_w + 2) + br)
    return lines


def _assign_layers(
    nodes: dict[int, GraphNode], edges: tuple[GraphEdge, ...]
) -> dict[int, int]:
    """Longest-path layering on the DAG; BFS fallback when cycles remain."""
    if not nodes:
        return {}

    indegree: dict[int, int] = {nid: 0 for nid in nodes}
    outgoing: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        if edge.src in nodes and edge.dest in nodes and edge.src != edge.dest:
            indegree[edge.dest] = indegree.get(edge.dest, 0) + 1
            outgoing[edge.src].append(edge.dest)

    # Kahn topological order + longest-path relax.
    indegree_work = dict(indegree)
    queue: deque[int] = deque(sorted(nid for nid, d in indegree_work.items() if d == 0))
    topo: list[int] = []
    while queue:
        cur = queue.popleft()
        topo.append(cur)
        for nxt in outgoing.get(cur, []):
            indegree_work[nxt] -= 1
            if indegree_work[nxt] == 0:
                queue.append(nxt)

    layer: dict[int, int] = {nid: 0 for nid in nodes}
    if len(topo) == len(nodes):
        for cur in topo:
            for nxt in outgoing.get(cur, []):
                layer[nxt] = max(layer[nxt], layer[cur] + 1)
        return layer

    # Cyclic: BFS first-reach from roots (or min id).
    layer = {}
    roots = [nid for nid, deg in indegree.items() if deg == 0]
    if not roots:
        roots = [min(nodes)]
    bfs: deque[int] = deque()
    for r in sorted(roots):
        layer[r] = 0
        bfs.append(r)
    while bfs:
        cur = bfs.popleft()
        for nxt in outgoing.get(cur, []):
            if nxt not in layer:
                layer[nxt] = layer[cur] + 1
                bfs.append(nxt)
    for nid in nodes:
        if nid not in layer:
            layer[nid] = 0
    return layer


def _barycentric_order(
    by_layer: dict[int, list[int]],
    layers: dict[int, int],
    edges: tuple[GraphEdge, ...],
    max_layer: int,
    passes: int = 2,
) -> dict[int, list[int]]:
    """Reorder node ids within each layer to reduce edge crossings."""
    order = {L: list(ids) for L, ids in by_layer.items()}
    for L in range(max_layer + 1):
        order.setdefault(L, [])
        order[L].sort()

    forward = defaultdict(list)
    backward = defaultdict(list)
    for edge in edges:
        if edge.src not in layers or edge.dest not in layers:
            continue
        forward[edge.src].append(edge.dest)
        backward[edge.dest].append(edge.src)

    def _reorder(layer_idx: int, neighbors_of: dict[int, list[int]], ref_layer: int) -> None:
        ref_pos = {nid: i for i, nid in enumerate(order.get(ref_layer, []))}
        if not ref_pos:
            return

        def key(nid: int) -> tuple[float, int]:
            nbrs = [ref_pos[n] for n in neighbors_of.get(nid, []) if n in ref_pos]
            if not nbrs:
                return (float(len(ref_pos)), nid)
            return (sum(nbrs) / len(nbrs), nid)

        order[layer_idx] = sorted(order[layer_idx], key=key)

    for _ in range(passes):
        for L in range(1, max_layer + 1):
            _reorder(L, backward, L - 1)
        for L in range(max_layer - 1, -1, -1):
            _reorder(L, forward, L + 1)
    return order


class _Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.grid = [[" " for _ in range(width)] for _ in range(height)]
        self.styles: list[list[str | None]] = [
            [None for _ in range(width)] for _ in range(height)
        ]
        self.blocked: set[tuple[int, int]] = set()

    def blit_box(
        self, x0: int, y0: int, lines: list[str], *, style: str | None = None
    ) -> None:
        for dy, line in enumerate(lines):
            for dx, ch in enumerate(line):
                xx, yy = x0 + dx, y0 + dy
                if 0 <= yy < self.height and 0 <= xx < self.width:
                    self.grid[yy][xx] = ch
                    # Color only the box border; keep label/id/props unstyled.
                    self.styles[yy][xx] = (
                        style if style is not None and ch in _BOX_BORDER_CHARS else None
                    )
                    self.blocked.add((xx, yy))

    def put(
        self,
        x: int,
        y: int,
        ch: str,
        *,
        force: bool = False,
        style: str | None = None,
    ) -> None:
        if not (0 <= y < self.height and 0 <= x < self.width):
            return
        if (x, y) in self.blocked and not force:
            return
        cur = self.grid[y][x]
        if cur in {" ", ch}:
            self.grid[y][x] = ch
            if style is not None:
                self.styles[y][x] = style
            return
        if ch in {" ", ""}:
            return
        self.grid[y][x] = _MERGE.get((cur, ch), _MERGE.get((ch, cur), ch))
        if style is not None:
            self.styles[y][x] = style

    def hline(
        self,
        x0: int,
        x1: int,
        y: int,
        tip: str | None = None,
        *,
        style: str | None = None,
    ) -> None:
        if x0 > x1:
            x0, x1 = x1, x0
            if tip == "▶":
                tip_left, tip_right = "◀", None
            else:
                tip_left, tip_right = tip, None
        else:
            tip_left, tip_right = None, tip
        for x in range(x0, x1 + 1):
            self.put(x, y, "─", style=style)
        if tip_right:
            self.put(x1, y, tip_right, style=style)
        if tip_left:
            self.put(x0, y, tip_left, style=style)

    def vline(
        self,
        x: int,
        y0: int,
        y1: int,
        tip: str | None = None,
        *,
        style: str | None = None,
    ) -> None:
        if y0 > y1:
            y0, y1 = y1, y0
            if tip == "▼":
                tip_top, tip_bot = "▲", None
            elif tip == "▲":
                tip_top, tip_bot = None, "▼"
            else:
                tip_top, tip_bot = tip, None
        else:
            tip_top, tip_bot = None, tip
        for y in range(y0, y1 + 1):
            self.put(x, y, "│", style=style)
        if tip_bot:
            self.put(x, y1, tip_bot, style=style)
        if tip_top:
            self.put(x, y0, tip_top, style=style)

    def label(
        self, x: int, y: int, text: str, *, style: str | None = None
    ) -> None:
        for i, ch in enumerate(text):
            xx = x + i
            if 0 <= y < self.height and 0 <= xx < self.width:
                if (xx, y) in self.blocked:
                    continue
                if self.grid[y][xx] in {" ", "─", "│"}:
                    self.grid[y][xx] = ch
                    self.styles[y][xx] = style

    def _trim_bounds(self) -> tuple[int, int]:
        """Return (top, bottom_exclusive) after stripping blank rows."""
        top = 0
        bottom = self.height
        while top < bottom and not any(ch != " " for ch in self.grid[top]):
            top += 1
        while bottom > top and not any(ch != " " for ch in self.grid[bottom - 1]):
            bottom -= 1
        return top, bottom

    def render(self) -> str:
        top, bottom = self._trim_bounds()
        lines = ["".join(row).rstrip() for row in self.grid[top:bottom]]
        return "\n".join(lines)

    def render_rich(self) -> Text:
        top, bottom = self._trim_bounds()
        out = Text()
        for yi, y in enumerate(range(top, bottom)):
            if yi:
                out.append("\n")
            row = self.grid[y]
            styles = self.styles[y]
            # Trim trailing spaces for width, keep styles aligned.
            end = len(row)
            while end > 0 and row[end - 1] == " ":
                end -= 1
            i = 0
            while i < end:
                style = styles[i]
                j = i + 1
                while j < end and styles[j] == style:
                    j += 1
                chunk = "".join(row[i:j])
                if style:
                    out.append(chunk, style=style)
                else:
                    out.append(chunk)
                i = j
        return out


def _port_right(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    return x1, y0 + (y1 - y0) // 2


def _port_left(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    return x0, y0 + (y1 - y0) // 2


def _port_bottom(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    return x0 + (x1 - x0) // 2, y1


def _port_top(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    return x0 + (x1 - x0) // 2, y0


def _draw_edge_label(
    canvas: _Canvas,
    label: str,
    x0: int,
    x1: int,
    y: int,
    *,
    style: str | None = None,
) -> None:
    if x0 > x1:
        x0, x1 = x1, x0
    span = x1 - x0 + 1
    if span < 2 or not label:
        return
    text = label if len(label) <= span else label[: max(1, span - 1)] + "…"
    label_y = y - 1 if y > 0 else y
    label_x = x0 + max(0, (span - len(text)) // 2)
    canvas.label(label_x, label_y, text, style=None)


def _route_forward_adjacent(
    canvas: _Canvas,
    src: tuple[int, int, int, int],
    dest: tuple[int, int, int, int],
    label: str,
    *,
    style: str | None = None,
) -> None:
    sx, sy = _port_right(src)
    dx, dy = _port_left(dest)
    x_start = sx + 1
    x_elbow = dx - 1
    if x_elbow < x_start:
        return
    canvas.hline(x_start, x_elbow, sy, style=style)
    if sy != dy:
        canvas.vline(x_elbow, sy, dy, style=style)
        corner = "┐" if dy > sy else "┘"
        canvas.put(x_elbow, sy, corner, style=style)
        canvas.put(x_elbow, dy, "│", style=style)
    canvas.put(x_elbow, dy, "▶" if x_elbow == dx - 1 else "─", style=style)
    if x_elbow < dx - 1:
        canvas.hline(x_elbow, dx - 1, dy, tip="▶", style=style)
    else:
        canvas.put(dx - 1, dy, "▶", style=style)
    _draw_edge_label(canvas, label, x_start, x_elbow, sy, style=style)


def _route_forward_skip(
    canvas: _Canvas,
    src: tuple[int, int, int, int],
    dest: tuple[int, int, int, int],
    label: str,
    channel_y: int,
    *,
    style: str | None = None,
) -> None:
    sx, sy = _port_right(src)
    dx, dy = _port_left(dest)
    x_out = sx + 1
    x_in = dx - 1
    if x_in < x_out:
        return
    canvas.vline(x_out, min(sy, channel_y), max(sy, channel_y), style=style)
    canvas.put(x_out, sy, "┐" if channel_y < sy else "┘", style=style)
    canvas.hline(x_out, x_in, channel_y, style=style)
    canvas.put(x_out, channel_y, "┌" if channel_y < sy else "└", style=style)
    canvas.put(x_in, channel_y, "┐" if channel_y < dy else "┘", style=style)
    canvas.vline(x_in, min(dy, channel_y), max(dy, channel_y), style=style)
    canvas.put(x_in, dy, "▶", style=style)
    _draw_edge_label(canvas, label, x_out, x_in, channel_y, style=style)


def _route_same_layer(
    canvas: _Canvas,
    src: tuple[int, int, int, int],
    dest: tuple[int, int, int, int],
    label: str,
    channel_y: int,
    *,
    style: str | None = None,
) -> None:
    sx, sy = _port_bottom(src)
    dx, dy = _port_bottom(dest)
    canvas.vline(sx, sy + 1, channel_y, style=style)
    canvas.vline(dx, dy + 1, channel_y, style=style)
    canvas.put(sx, channel_y, "└", style=style)
    canvas.put(dx, channel_y, "┘", style=style)
    if sx < dx:
        canvas.hline(sx, dx, channel_y, style=style)
        canvas.put(dx, dy + 1, "▲", style=style)
    else:
        canvas.hline(dx, sx, channel_y, style=style)
        canvas.put(dx, dy + 1, "▲", style=style)
    _draw_edge_label(canvas, label, min(sx, dx), max(sx, dx), channel_y, style=style)


def _route_back_edge(
    canvas: _Canvas,
    src: tuple[int, int, int, int],
    dest: tuple[int, int, int, int],
    label: str,
    channel_y: int,
    *,
    style: str | None = None,
) -> None:
    sx, sy = _port_bottom(src)
    dx, dy = _port_bottom(dest)
    canvas.vline(sx, sy + 1, channel_y, style=style)
    canvas.vline(dx, dy + 1, channel_y, style=style)
    canvas.put(sx, channel_y, "└", style=style)
    canvas.put(dx, channel_y, "┘", style=style)
    lo, hi = (sx, dx) if sx < dx else (dx, sx)
    canvas.hline(lo, hi, channel_y, style=style)
    canvas.put(dx, dy + 1, "▲", style=style)
    _draw_edge_label(canvas, label, lo, hi, channel_y, style=style)


def _node_style(node: GraphNode, *, selected: bool) -> str:
    base = color_for(node.labels[0]) if node.labels else "white"
    return f"bold {base}" if selected else base


def _edge_style(edge: GraphEdge) -> str:
    return color_for(edge.type)


def layout_ascii(
    model: GraphViewModel,
    *,
    selected_id: int | None = None,
    include_header: bool = True,
    display: GraphDisplayOptions | None = None,
) -> AsciiCanvas:
    if not model.nodes:
        return AsciiCanvas(
            text=EMPTY_MESSAGE,
            hitboxes=(),
            node_order=(),
            rich=Text(EMPTY_MESSAGE, style="dim"),
        )

    nodes = {n.id: n for n in model.nodes}
    layers = _assign_layers(nodes, model.edges)
    max_layer = max(layers.values()) if layers else 0

    by_layer_ids: dict[int, list[int]] = defaultdict(list)
    for node in model.nodes:
        by_layer_ids[layers[node.id]].append(node.id)

    ordered = _barycentric_order(by_layer_ids, layers, model.edges, max_layer)

    box_lines_cache = {
        nid: _box_lines(
            nodes[nid], selected=(nid == selected_id), display=display
        )
        for nid in nodes
    }
    box_heights = {nid: len(lines) for nid, lines in box_lines_cache.items()}
    max_box_h = max(box_heights.values(), default=4)

    max_label = max((len(e.type) for e in model.edges), default=8)
    col_gap = max(12, max_label + 4)

    col_widths: dict[int, int] = {}
    for layer_idx, ids in ordered.items():
        if not ids:
            col_widths[layer_idx] = 10
            continue
        col_widths[layer_idx] = max(len(box_lines_cache[nid][0]) for nid in ids)

    # Vertical packing with gap for same-layer under-routing.
    row_gap = 2
    row_pitch = max_box_h + row_gap
    max_rows = max((len(v) for v in ordered.values()), default=0)

    top_margin = 2  # skip-edge channels
    bottom_margin = 3  # back / same-layer channels

    col_x: dict[int, int] = {}
    x = 0
    for layer_idx in range(max_layer + 1):
        col_x[layer_idx] = x
        x += col_widths.get(layer_idx, 10) + col_gap

    width = max(x - col_gap + 1, 40)
    height = top_margin + max_rows * row_pitch + bottom_margin

    canvas = _Canvas(width, height)
    hitboxes: list[Hitbox] = []
    node_pos: dict[int, tuple[int, int, int, int]] = {}
    node_order: list[int] = []

    for layer_idx in range(max_layer + 1):
        for row_i, nid in enumerate(ordered.get(layer_idx, [])):
            lines = box_lines_cache[nid]
            x0 = col_x[layer_idx]
            y0 = top_margin + row_i * row_pitch
            style = _node_style(nodes[nid], selected=(nid == selected_id))
            canvas.blit_box(x0, y0, lines, style=style)
            x1 = x0 + len(lines[0]) - 1
            y1 = y0 + len(lines) - 1
            hitboxes.append(Hitbox(node_id=nid, x0=x0, y0=y0, x1=x1, y1=y1))
            node_pos[nid] = (x0, y0, x1, y1)
            node_order.append(nid)

    # Channel counters for stacking parallel routes.
    skip_channel = 0
    bottom_channel = 0
    undrawn: list[GraphEdge] = []

    for edge in model.edges:
        if edge.src not in node_pos or edge.dest not in node_pos:
            undrawn.append(edge)
            continue
        style = _edge_style(edge)
        label = edge.type
        if edge.src == edge.dest:
            # Self-loop: simple bottom hook.
            box = node_pos[edge.src]
            sx, sy = _port_bottom(box)
            cy = height - 2 - bottom_channel
            bottom_channel += 1
            canvas.vline(sx, sy + 1, cy, style=style)
            canvas.put(sx, cy, "└", style=style)
            canvas.hline(sx, min(sx + 3, width - 1), cy, style=style)
            canvas.put(min(sx + 3, width - 1), cy, "┘", style=style)
            canvas.vline(min(sx + 3, width - 1), cy, sy + 1, style=style)
            canvas.put(min(sx + 3, width - 1), sy + 1, "▲", style=style)
            _draw_edge_label(
                canvas, label, sx, min(sx + 3, width - 1), cy, style=style
            )
            continue

        src_l = layers[edge.src]
        dest_l = layers[edge.dest]
        src_box = node_pos[edge.src]
        dest_box = node_pos[edge.dest]

        if dest_l == src_l + 1:
            _route_forward_adjacent(
                canvas, src_box, dest_box, label, style=style
            )
        elif dest_l > src_l + 1:
            channel_y = max(0, top_margin - 1 - skip_channel)
            skip_channel = min(skip_channel + 1, top_margin)
            _route_forward_skip(
                canvas, src_box, dest_box, label, channel_y, style=style
            )
        elif dest_l == src_l:
            channel_y = height - 2 - bottom_channel
            bottom_channel += 1
            _route_same_layer(
                canvas, src_box, dest_box, label, channel_y, style=style
            )
        else:
            # Back-edge
            channel_y = height - 2 - bottom_channel
            bottom_channel += 1
            _route_back_edge(
                canvas, src_box, dest_box, label, channel_y, style=style
            )

    body = canvas.render()
    body_rich = canvas.render_rich()
    plain_parts: list[str] = []
    rich = Text()
    if include_header:
        if model.truncated:
            header = (
                f"showing {len(model.nodes)}/{model.total_nodes} nodes · "
                f"{len(model.edges)}/{model.total_edges} edges (truncated)"
            )
        else:
            header = f"{len(model.nodes)} nodes · {len(model.edges)} edges"
        plain_parts.append(header)
        rich.append(header, style="dim")
        rich.append("\n")
    plain_parts.append(body)
    rich.append_text(body_rich)
    if undrawn:
        plain_parts.append("other edges:")
        rich.append("\n")
        rich.append("other edges:", style="dim")
        for e in undrawn:
            line = f"({e.src})-{e.type}->({e.dest})"
            plain_parts.append(line)
            rich.append("\n")
            rich.append(line)
    text = "\n".join(plain_parts)

    return AsciiCanvas(
        text=text,
        hitboxes=tuple(hitboxes),
        node_order=tuple(node_order),
        rich=rich,
    )
