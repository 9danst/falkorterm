from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.layout_coords import layout_coords


def _node(nid: int, *labels: str) -> GraphNode:
    labs = labels or ("Person",)
    return GraphNode(
        id=nid,
        labels=tuple(labs),
        properties={},
        display=f"(:{':'.join(labs)} id={nid})",
    )


def _edge(src: int, dest: int, typ: str = "KNOWS") -> GraphEdge:
    return GraphEdge(src=src, dest=dest, type=typ)


def test_layout_empty():
    geo = layout_coords(
        GraphViewModel(nodes=(), edges=()), width=40, height=20
    )
    assert geo.nodes == ()
    assert geo.edges == ()
    assert geo.width == 40


def test_layout_layered_two_nodes():
    model = GraphViewModel(
        nodes=(_node(1), _node(2)),
        edges=(_edge(1, 2),),
    )
    geo = layout_coords(model, width=40, height=20)
    assert geo.node_order == (1, 2)
    assert len(geo.edges) == 1
    by_id = {n.id: n for n in geo.nodes}
    # Layered L→R: source left of dest after fit
    assert by_id[1].x < by_id[2].x
    for n in geo.nodes:
        assert 0 <= n.x <= 40
        assert 0 <= n.y <= 20


def test_layout_ego_focus_centerish():
    model = GraphViewModel(
        nodes=(_node(1), _node(2), _node(3)),
        edges=(_edge(1, 2), _edge(1, 3)),
    )
    geo = layout_coords(model, width=40, height=20, focus_id=1)
    by_id = {n.id: n for n in geo.nodes}
    # Focus near canvas center after auto-fit
    assert abs(by_id[1].x - 20) < 3
    assert abs(by_id[1].y - 10) < 3
    # Neighbors farther from center than focus
    d2 = (by_id[2].x - by_id[1].x) ** 2 + (by_id[2].y - by_id[1].y) ** 2
    d3 = (by_id[3].x - by_id[1].x) ** 2 + (by_id[3].y - by_id[1].y) ** 2
    assert d2 > 1
    assert d3 > 1


def test_layout_edge_order_stable():
    model = GraphViewModel(
        nodes=(_node(1), _node(2), _node(3)),
        edges=(_edge(1, 2, "A"), _edge(2, 3, "B")),
    )
    geo = layout_coords(model, width=50, height=20)
    assert len(geo.edge_order) == 2
    assert geo.edge_order == tuple(e.key for e in geo.edges)
