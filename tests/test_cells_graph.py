from types import SimpleNamespace

from falkorterm.client.cells import to_cell_value


def test_edge_includes_src_dest():
    edge = SimpleNamespace(
        relation="KNOWS", properties={}, id=9, src_node=1, dest_node=2
    )
    cell = to_cell_value(edge)
    assert cell.detail is not None
    assert cell.detail["kind"] == "edge"
    assert cell.detail["src"] == 1
    assert cell.detail["dest"] == 2


def test_edge_resolves_node_objects_for_endpoints():
    src = SimpleNamespace(id=10)
    dest = SimpleNamespace(id=20)
    edge = SimpleNamespace(
        relation="LIKES", properties={"w": 1}, id=3, src_node=src, dest_node=dest
    )
    cell = to_cell_value(edge)
    assert cell.detail is not None
    assert cell.detail["src"] == 10
    assert cell.detail["dest"] == 20
    assert cell.detail["id"] == 3


def test_path_includes_nodes_and_edges_via_methods():
    n1 = SimpleNamespace(labels=["Person"], properties={}, id=1)
    n2 = SimpleNamespace(labels=["Person"], properties={}, id=2)
    e = SimpleNamespace(relation="KNOWS", properties={}, id=9, src_node=1, dest_node=2)
    path = SimpleNamespace(
        nodes=lambda: [n1, n2],
        edges=lambda: [e],
    )
    cell = to_cell_value(path)
    assert cell.detail is not None
    assert cell.detail["kind"] == "path"
    assert len(cell.detail["nodes"]) == 2
    assert cell.detail["edges"][0]["src"] == 1
    assert cell.detail["edges"][0]["dest"] == 2
    assert cell.detail["edges"][0]["type"] == "KNOWS"
