from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_surf import render_surf
from falkorterm.graph.session import SurfSession


def _n(i: int, name: str | None = None, **props: object) -> GraphNode:
    properties = {"name": name or f"n{i}", **props}
    return GraphNode(
        id=i,
        labels=("Person",),
        properties=properties,
        display=name or f"n{i}",
    )


def _model(*nodes: GraphNode, edges: tuple[GraphEdge, ...] = ()) -> GraphViewModel:
    return GraphViewModel(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


def test_render_empty_session():
    text = render_surf(SurfSession()).plain
    assert "No graph data" in text or "no graph" in text.lower()


def test_render_shows_focus_out_in_and_cursor():
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

    assert "Alice" in plain
    assert "FOCUS" in plain
    assert "name=Alice" in plain
    assert "age=34" in plain
    assert "city=BCN" in plain
    assert "role=dev" not in plain
    assert "OUT 1" in plain
    assert "KNOWS" in plain
    assert "Bob" in plain
    assert "IN 1" in plain
    assert "FOLLOWS" in plain
    assert "Dana" in plain
    assert "▸" in plain


def test_render_emphasizes_selected_edge_kind():
    s = SurfSession()
    s.seed(_model(_n(1, "Alice"), _n(2, "Bob"), edges=(GraphEdge(1, 2, "KNOWS"),)))
    s.cycle_neighbor(+1)
    s.toggle_kind()

    plain = render_surf(s).plain

    assert "«KNOWS»" in plain


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

    assert "trail:" in plain
    assert "n1" not in plain.splitlines()[0]
    assert "n2" in plain.splitlines()[0]
    assert "[:R23]" in plain
    assert "[:R67]" in plain
