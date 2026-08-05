from falkorterm.graph.colors import EMPTY_MESSAGE, color_for
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_text import node_caption, render_graph_text


def _node(nid: int, label: str = "Person", **props: object) -> GraphNode:
    return GraphNode(
        id=nid,
        labels=(label,),
        properties=dict(props),
        display=f"(:{label} id={nid})",
    )


def test_empty_message():
    text = render_graph_text(GraphViewModel(nodes=(), edges=()))
    assert text.plain == EMPTY_MESSAGE


def test_neighborhood_shows_outbound_and_labels():
    model = GraphViewModel(
        nodes=(
            _node(1, "Airport", name="ANC"),
            _node(2, "Airport", name="JFK"),
            _node(3, "Country", name="US"),
        ),
        edges=(
            GraphEdge(src=1, dest=2, type="FLIES_TO"),
            GraphEdge(src=3, dest=1, type="IN_COUNTRY"),
        ),
    )
    text = render_graph_text(model, selected_id=1, select_kind="node")
    plain = text.plain
    assert "Selected" in plain
    assert "id=1" in plain
    assert "name=ANC" in plain
    assert "Outbound (1)" in plain
    assert "FLIES_TO" in plain
    assert "JFK" in plain
    assert "Inbound (1)" in plain
    assert "IN_COUNTRY" in plain
    assert "US" in plain


def test_edge_mode_lists_all_edges_with_selection():
    model = GraphViewModel(
        nodes=(_node(1), _node(2)),
        edges=(GraphEdge(src=1, dest=2, type="KNOWS"),),
    )
    from falkorterm.graph.extract import edge_key

    key = edge_key(model.edges[0])
    text = render_graph_text(
        model, select_kind="edge", selected_edge_key=key
    )
    plain = text.plain
    assert "All edges" in plain
    assert "«KNOWS»" in plain
    assert "»" in plain


def test_node_caption_and_colors():
    n = _node(16, "Airport", name="ANC")
    assert "id=16" in node_caption(n)
    assert "ANC" in node_caption(n)
    assert color_for("Airport") == color_for("Airport")
