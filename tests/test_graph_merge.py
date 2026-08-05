from falkorterm.graph.merge import merge_graphs
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


def _node(
    nid: int,
    *,
    labels: tuple[str, ...] = ("Person",),
    properties: dict[str, object] | None = None,
    display: str = "",
) -> GraphNode:
    labs = labels
    disp = display or (f"(:{':'.join(labs)} id={nid})" if labs else f"(node id={nid})")
    return GraphNode(
        id=nid,
        labels=labs,
        properties=dict(properties or {}),
        display=disp,
    )


def _edge(
    src: int,
    dest: int,
    *,
    typ: str = "KNOWS",
    eid: int | None = None,
    properties: dict[str, object] | None = None,
) -> GraphEdge:
    return GraphEdge(
        src=src,
        dest=dest,
        type=typ,
        id=eid,
        properties=dict(properties or {}),
    )


def test_merge_dedupes_nodes_and_edges_preserves_base_then_incoming_order():
    base = GraphViewModel(
        nodes=(_node(1), _node(2)),
        edges=(_edge(1, 2, eid=9),),
        total_nodes=2,
        total_edges=1,
    )
    incoming = GraphViewModel(
        nodes=(_node(2), _node(3)),
        edges=(_edge(1, 2, eid=9), _edge(2, 3, eid=10)),
        total_nodes=2,
        total_edges=2,
    )
    merged = merge_graphs(base, incoming)
    assert [n.id for n in merged.nodes] == [1, 2, 3]
    assert [(e.src, e.dest, e.id) for e in merged.edges] == [
        (1, 2, 9),
        (2, 3, 10),
    ]
    assert merged.truncated is False
    assert merged.total_nodes == 3
    assert merged.total_edges == 2


def test_merge_upgrades_placeholder_node():
    base = GraphViewModel(
        nodes=(_node(1, labels=(), display="(node id=1)"),),
        edges=(),
        total_nodes=1,
        total_edges=0,
    )
    incoming = GraphViewModel(
        nodes=(
            _node(
                1,
                labels=("Person",),
                properties={"name": "Ada"},
                display="(:Person id=1)",
            ),
        ),
        edges=(),
        total_nodes=1,
        total_edges=0,
    )
    merged = merge_graphs(base, incoming)
    assert len(merged.nodes) == 1
    node = merged.nodes[0]
    assert node.labels == ("Person",)
    assert node.properties == {"name": "Ada"}
    assert "Person" in node.display


def test_merge_applies_session_caps_and_truncated():
    base_nodes = tuple(_node(i) for i in range(40))
    base = GraphViewModel(
        nodes=base_nodes,
        edges=tuple(_edge(i, i + 1, eid=i) for i in range(39)),
        total_nodes=40,
        total_edges=39,
    )
    incoming = GraphViewModel(
        nodes=tuple(_node(i) for i in range(40, 60)),
        edges=tuple(_edge(i, i + 1, eid=i) for i in range(39, 59)),
        total_nodes=20,
        total_edges=20,
    )
    merged = merge_graphs(base, incoming, max_nodes=50, max_edges=80)
    assert len(merged.nodes) == 50
    assert merged.total_nodes == 60
    assert merged.truncated is True
    # Edges kept only when both endpoints remain after node cap.
    assert len(merged.edges) <= 80
    kept = {n.id for n in merged.nodes}
    for e in merged.edges:
        assert e.src in kept and e.dest in kept
