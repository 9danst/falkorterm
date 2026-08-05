from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.layout import layout_ascii
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


def _style_at(text, index: int) -> str:
    for start, end, style in text.spans:
        if start <= index < end:
            return str(style or "")
    return ""


def test_layout_two_nodes_edge():
    model = GraphViewModel(
        nodes=(
            GraphNode(id=1, labels=("Person",), properties={}, display="(:Person id=1)"),
            GraphNode(id=2, labels=("Person",), properties={}, display="(:Person id=2)"),
        ),
        edges=(GraphEdge(src=1, dest=2, type="KNOWS", id=9),),
        total_nodes=2,
        total_edges=1,
    )
    canvas = layout_ascii(model)
    assert "id=1" in canvas.text
    assert "id=2" in canvas.text
    assert "KNOWS" in canvas.text
    assert "[:KNOWS]" not in canvas.text
    hb = next(h for h in canvas.hitboxes if h.node_id == 1)
    assert hb.x1 >= hb.x0
    assert hb.y1 >= hb.y0
    assert canvas.node_order == (1, 2)


def test_layout_empty_message():
    canvas = layout_ascii(GraphViewModel(nodes=(), edges=()))
    assert canvas.text == EMPTY_MESSAGE
    assert canvas.hitboxes == ()
    assert canvas.node_order == ()


def test_layout_colors_only_borders_and_edge_strokes():
    model = GraphViewModel(
        nodes=(
            GraphNode(id=1, labels=("Person",), properties={}, display="(:Person id=1)"),
            GraphNode(id=2, labels=("Movie",), properties={}, display="(:Movie id=2)"),
        ),
        edges=(GraphEdge(src=1, dest=2, type="ACTED_IN", id=9),),
        total_nodes=2,
        total_edges=1,
    )
    canvas = layout_ascii(model)
    assert canvas.rich is not None
    plain = canvas.rich.plain

    border_idx = plain.index("┌")
    assert color_for("Person") in _style_at(canvas.rich, border_idx)

    content_idx = plain.index("id=1")
    assert color_for("Person") not in _style_at(canvas.rich, content_idx)
    assert "bold" not in _style_at(canvas.rich, content_idx)

    movie_label_idx = plain.index(":Movie")
    assert color_for("Movie") not in _style_at(canvas.rich, movie_label_idx)

    arrow_idx = plain.index("▶")
    assert color_for("ACTED_IN") in _style_at(canvas.rich, arrow_idx)

    edge_name_idx = plain.index("ACTED_IN")
    assert color_for("ACTED_IN") not in _style_at(canvas.rich, edge_name_idx)

    assert "ACTED_IN" in plain
    assert "[:ACTED_IN]" not in plain


def test_layout_same_label_same_border_color():
    model = GraphViewModel(
        nodes=(
            GraphNode(id=1, labels=("Person",), properties={}, display="(:Person id=1)"),
            GraphNode(id=2, labels=("Person",), properties={}, display="(:Person id=2)"),
        ),
        edges=(),
        total_nodes=2,
        total_edges=0,
    )
    canvas = layout_ascii(model)
    assert canvas.rich is not None
    plain = canvas.rich.plain
    first = plain.index("┌")
    second = plain.index("┌", first + 1)
    assert color_for("Person") in _style_at(canvas.rich, first)
    assert color_for("Person") in _style_at(canvas.rich, second)
