from falkorterm.graph.colors import color_for
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_surf import render_surf, surf_hint
from falkorterm.graph.session import SurfSession


def _style_at(text, index: int) -> str:
    for start, end, style in text.spans:
        if start <= index < end:
            return str(style or "")
    return ""


def _style_of(text, needle: str, *, occurrence: int = 0) -> str:
    start = -1
    for _ in range(occurrence + 1):
        start = text.plain.find(needle, start + 1)
        if start < 0:
            raise AssertionError(f"{needle!r} not found (occurrence={occurrence})")
    return _style_at(text, start)


def _n(i: int, name: str | None = None, **props: object) -> GraphNode:
    properties = {"name": name or f"n{i}", **props}
    return GraphNode(
        id=i,
        labels=("Person",),
        properties=properties,
        display=name or f"n{i}",
    )


def _model(
    *nodes: GraphNode,
    edges: tuple[GraphEdge, ...] = (),
    truncated: bool = False,
) -> GraphViewModel:
    return GraphViewModel(
        nodes=nodes,
        edges=edges,
        truncated=truncated,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


def test_render_empty_session():
    text = render_surf(SurfSession()).plain
    assert "No graph data" in text or "no graph" in text.lower()


def test_render_shows_focus_box_out_in_and_cursor():
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "Alice", age=34, city="BCN", role="dev"),
            _n(2, "Bob"),
            _n(3, "Dana"),
            edges=(
                GraphEdge(src=1, dest=2, type="KNOWS", id=9),
                GraphEdge(src=3, dest=1, type="FOLLOWS", id=10),
            ),
        )
    )
    s.cycle_neighbor(+1)

    plain = render_surf(s).plain

    assert "┏" in plain
    assert "FOCUS · OUT 1 · IN 1 · NODE" in plain
    assert "Alice" in plain
    assert "name=Alice" in plain
    assert "age=34" in plain
    assert "city=BCN" in plain
    assert "role=dev" not in plain
    assert "OUT 1" in plain
    assert "KNOWS" in plain
    assert "Bob" in plain
    assert "name=Bob" in plain
    assert "IN 1" in plain
    assert "FOLLOWS" in plain
    assert "Dana" in plain
    assert "▸" in plain
    assert "── selected" in plain
    assert "via [:KNOWS]" in plain
    assert "depth 1 · jump 1/1" in plain


def test_render_emphasizes_selected_edge_kind():
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), _n(2, "Bob"), edges=(GraphEdge(1, 2, "KNOWS"),)))
    s.cycle_neighbor(+1)
    s.toggle_kind()

    plain = render_surf(s).plain

    assert "«KNOWS»" in plain
    assert "FOCUS · OUT 1 · IN 0 · EDGE" in plain


def test_render_header_marks_truncated_model():
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), truncated=True))

    plain = render_surf(s).plain

    assert "session: 1 nodes · 0 edges · truncated" in plain


def test_render_trail_uses_last_six_jump_entries_with_edge_types():
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "n1"),
            _n(2, "n2"),
            _n(3, "n3"),
            _n(4, "n4"),
            _n(5, "n5"),
            _n(6, "n6"),
            _n(7, "n7"),
            edges=(
                GraphEdge(1, 2, "R12"),
                GraphEdge(2, 3, "R23"),
                GraphEdge(3, 4, "R34"),
                GraphEdge(4, 5, "R45"),
                GraphEdge(5, 6, "R56"),
                GraphEdge(6, 7, "R67"),
            ),
        )
    )
    for _ in range(6):
        s.cycle_neighbor(+1)
        s.hop()

    plain = render_surf(s).plain
    trail = plain.splitlines()[0]

    assert "trail:" in trail
    assert "…" in trail or "..." in trail
    assert "n1" not in trail
    assert "n2" in trail
    assert "[:R23]" in plain
    assert "[:R67]" in plain
    assert "depth 7 · jump 7/7" in plain


def test_render_trail_respects_jump_index_after_jump_back():
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "Alice"),
            _n(2, "Bob"),
            _n(3, "Carol"),
            edges=(
                GraphEdge(1, 2, "KNOWS"),
                GraphEdge(2, 3, "FOLLOWS"),
            ),
        )
    )
    s.cycle_neighbor(+1)
    s.hop()
    s.cycle_neighbor(+1)
    s.hop()
    s.jump_back()

    trail = render_surf(s).plain.splitlines()[0]

    assert trail == "trail: Alice → [:KNOWS] → Bob"
    assert "depth 2 · jump 2/3" in render_surf(s).plain


def test_surf_hint_changes_with_selection_kind():
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), _n(2, "Bob"), edges=(GraphEdge(1, 2, "KNOWS"),)))

    assert "j/k neighbor" in surf_hint(s)
    assert "x expand" in surf_hint(s)

    s.cycle_neighbor(+1)
    assert "l hop" in surf_hint(s)
    assert "Tab edge" in surf_hint(s)

    s.toggle_kind()
    assert "Tab node" in surf_hint(s)
    assert "inspect edge" in surf_hint(s)


def test_selected_panel_omitted_without_neighbor_cursor():
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), _n(2, "Bob"), edges=(GraphEdge(1, 2, "KNOWS"),)))

    plain = render_surf(s).plain

    assert "── selected" not in plain
    assert surf_hint(s) in plain


def test_color_hierarchy_focus_caption_only_props_and_meta_dim():
    """Approach A: palette color only on primary captions; rest basic/dim."""
    person = color_for("Person")
    knows = color_for("KNOWS")
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "Alice", age=34, city="BCN"),
            _n(2, "Bob"),
            edges=(GraphEdge(1, 2, "KNOWS"),),
        )
    )

    text = render_surf(s)

    assert person in _style_of(text, "Alice")
    assert "bold" in _style_of(text, "Alice")
    assert "dim" in _style_of(text, ":Person")
    assert person not in _style_of(text, ":Person")
    assert "dim" in _style_of(text, "name=Alice")
    assert person not in _style_of(text, "name=Alice")
    assert "dim" in _style_of(text, "age=34")
    # unselected neighbor: caption default (no palette), rel dim
    assert person not in _style_of(text, "Bob")
    assert "bold" not in _style_of(text, "Bob")
    assert "dim" in _style_of(text, "[:KNOWS]")
    assert knows not in _style_of(text, "[:KNOWS]")


def test_color_hierarchy_selected_neighbor_and_panel():
    person = color_for("Person")
    knows = color_for("KNOWS")
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "Alice"),
            _n(2, "Bob"),
            edges=(GraphEdge(1, 2, "KNOWS"),),
        )
    )
    s.cycle_neighbor(+1)

    text = render_surf(s)

    bob_row = _style_of(text, "Bob")
    assert person in bob_row
    assert "bold" in bob_row
    assert "dim" in _style_of(text, ":Person", occurrence=1)  # neighbor labels
    assert person not in _style_of(text, "name=Bob")
    assert "dim" in _style_of(text, "[:KNOWS]")
    assert knows not in _style_of(text, "[:KNOWS]")

    # selected panel title caption colored; via dim
    panel_bob = text.plain.index("── selected")
    bob_in_panel = text.plain.index("Bob", panel_bob)
    assert person in _style_at(text, bob_in_panel)
    assert "bold" in _style_at(text, bob_in_panel)
    assert "dim" in _style_of(text, "via [:KNOWS]")
    assert knows not in _style_of(text, "via [:KNOWS]")


def test_color_hierarchy_edge_kind_bold_without_palette():
    knows = color_for("KNOWS")
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), _n(2, "Bob"), edges=(GraphEdge(1, 2, "KNOWS"),)))
    s.cycle_neighbor(+1)
    s.toggle_kind()

    text = render_surf(s)
    style = _style_of(text, "«KNOWS»")
    assert "bold" in style
    assert knows not in style


def test_color_hierarchy_trail_last_hop_colored_rest_dim():
    person = color_for("Person")
    knows = color_for("KNOWS")
    s = SurfSession()
    s.seed(
        _model(
            _n(1, "Alice"),
            _n(2, "Bob"),
            edges=(GraphEdge(1, 2, "KNOWS"),),
        )
    )
    s.cycle_neighbor(+1)
    s.hop()

    text = render_surf(s)
    assert "dim" in _style_of(text, "Alice")
    assert person not in _style_of(text, "Alice")
    assert "dim" in _style_of(text, "[:KNOWS]")
    assert knows not in _style_of(text, "[:KNOWS]")
    bob = _style_of(text, "Bob")
    assert person in bob
    assert "bold" in bob
