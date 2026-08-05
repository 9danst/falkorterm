from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel
from falkorterm.graph.session import SurfSession


def _n(i: int, **props: object) -> GraphNode:
    return GraphNode(
        id=i,
        labels=("Person",),
        properties=dict(props) if props else {"name": f"n{i}"},
        display=f"(:Person id={i})",
    )


def _e(src: int, dest: int, typ: str = "KNOWS", eid: int | None = None) -> GraphEdge:
    return GraphEdge(src=src, dest=dest, type=typ, id=eid)


def _model(*nodes: GraphNode, edges: tuple[GraphEdge, ...] = ()) -> GraphViewModel:
    return GraphViewModel(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


def test_seed_sets_focus_to_first_node_and_jump_list():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), edges=(_e(1, 2, eid=1),)))
    assert s.focus_id == 1
    assert s.seed_id == 1
    assert s.jump_list == [1]
    assert s.jump_index == 0
    assert s.neighbor_index == -1
    assert s.select_kind == "node"


def test_cycle_neighbor_and_hop_pushes_jump():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), _n(3), edges=(_e(1, 2, eid=1), _e(1, 3, eid=2))))
    s.cycle_neighbor(+1)
    assert s.neighbor_index == 0
    assert s.current_neighbor_id() == 2
    s.hop()
    assert s.focus_id == 2
    assert s.jump_list == [1, 2]
    assert s.neighbor_index == -1


def test_jump_back_and_forward():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), edges=(_e(1, 2, eid=1),)))
    s.cycle_neighbor(+1)
    s.hop()
    assert s.focus_id == 2
    assert s.jump_back() is True
    assert s.focus_id == 1
    assert s.jump_forward() is True
    assert s.focus_id == 2


def test_merge_keeps_focus_and_grows_model():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), edges=(_e(1, 2, eid=1),)))
    s.merge(_model(_n(1), _n(3), edges=(_e(1, 3, eid=2),)))
    assert s.focus_id == 1
    assert {n.id for n in s.model.nodes} == {1, 2, 3}


def test_merge_resets_edge_selection_to_node():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), edges=(_e(1, 2, eid=1),)))
    s.cycle_neighbor(+1)
    s.toggle_kind()
    assert s.select_kind == "edge"

    s.merge(_model(_n(1), _n(3), edges=(_e(1, 3, eid=2),)))

    assert s.select_kind == "node"


def test_toggle_kind_requires_neighbor_row():
    s = SurfSession()
    s.seed(_model(_n(1), _n(2), edges=(_e(1, 2, eid=1),)))
    assert s.toggle_kind() is False
    s.cycle_neighbor(+1)
    assert s.toggle_kind() is True
    assert s.select_kind == "edge"
