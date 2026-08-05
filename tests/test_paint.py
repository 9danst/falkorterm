from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.layout_coords import format_session_text
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_text import render_graph_text


def test_format_session_and_empty():
    assert format_session_text(GraphViewModel(nodes=(), edges=())) == EMPTY_MESSAGE
    model = GraphViewModel(
        nodes=(
            GraphNode(id=1, labels=("P",), properties={}, display="(:P id=1)"),
            GraphNode(id=2, labels=("P",), properties={}, display="(:P id=2)"),
        ),
        edges=(GraphEdge(src=1, dest=2, type="KNOWS"),),
    )
    assert "(1)-[:KNOWS]->(2)" in format_session_text(model)
    assert color_for("P")
    assert "Outbound" in render_graph_text(model, selected_id=1).plain
