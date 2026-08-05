from falkorterm.graph.colors import color_for
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_text import render_graph_text


def test_color_for_is_stable_and_from_palette():
    a = color_for("Person")
    b = color_for("Person")
    c = color_for("Movie")
    assert a == b
    assert a
    assert c


def test_render_uses_first_label_in_caption():
    model = GraphViewModel(
        nodes=(
            GraphNode(
                id=1, labels=("Person", "Actor"), properties={}, display="1"
            ),
        ),
        edges=(),
        total_nodes=1,
        total_edges=0,
    )
    plain = render_graph_text(model, selected_id=1).plain
    assert ":Person:Actor id=1" in plain


def test_render_includes_colored_edge_type():
    model = GraphViewModel(
        nodes=(
            GraphNode(id=1, labels=("A",), properties={}, display="1"),
            GraphNode(id=2, labels=("B",), properties={}, display="2"),
        ),
        edges=(GraphEdge(src=1, dest=2, type="KNOWS", id=9),),
        total_nodes=2,
        total_edges=1,
    )
    text = render_graph_text(model, selected_id=1)
    assert "KNOWS" in text.plain
    assert "Outbound (1)" in text.plain
