from falkorterm.graph.colors import EMPTY_MESSAGE
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.render_ego_ascii import ego_neighbors, render_ego_ascii


def _node(nid: int, label: str = "Airport", **props: object) -> GraphNode:
    return GraphNode(
        id=nid,
        labels=(label,),
        properties=dict(props),
        display=f"(:{label} id={nid})",
    )


def test_render_ego_empty():
    assert render_ego_ascii(GraphViewModel(nodes=(), edges=()), None).plain == EMPTY_MESSAGE


def test_render_ego_focus_and_neighbors():
    model = GraphViewModel(
        nodes=(_node(16, name="ANC"), _node(3, name="JFK"), _node(1, "Country", name="US")),
        edges=(
            GraphEdge(src=16, dest=3, type="FLIES_TO"),
            GraphEdge(src=1, dest=16, type="IN_COUNTRY"),
        ),
    )
    text = render_ego_ascii(model, 16, selected_neighbor_id=3)
    plain = text.plain
    assert "ego id=16" in plain
    assert "ANC" in plain
    assert "Neighbors" in plain
    assert "FLIES_TO" in plain
    assert "JFK" in plain
    assert "»" in plain


def test_ego_neighbors_lists_both_directions():
    model = GraphViewModel(
        nodes=(_node(1), _node(2), _node(3)),
        edges=(
            GraphEdge(src=1, dest=2, type="A"),
            GraphEdge(src=3, dest=1, type="B"),
        ),
    )
    nbrs = ego_neighbors(model, 1)
    assert len(nbrs) == 2
    dirs = {d for _, _, d in nbrs}
    assert dirs == {"out", "in"}
