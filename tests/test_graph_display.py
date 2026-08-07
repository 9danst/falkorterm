from falkorterm.graph.display import (
    GraphDisplayOptions,
    filter_graph,
    props_for_node,
    toggle_prop,
)
from falkorterm.graph.models import GraphEdge, GraphNode, GraphViewModel


def _node(
    nid: int,
    labels: tuple[str, ...],
    **props: object,
) -> GraphNode:
    return GraphNode(
        id=nid,
        labels=labels,
        properties=dict(props),
        display=f"(:{':'.join(labels) or 'node'} id={nid})",
    )


def test_filter_hides_label_and_incident_edges():
    model = GraphViewModel(
        nodes=(
            _node(1, ("Person",), name="Ada"),
            _node(2, ("Movie",), title="Matrix"),
            _node(3, ("Person",), name="Bob"),
        ),
        edges=(
            GraphEdge(src=1, dest=2, type="ACTED_IN", id=10),
            GraphEdge(src=1, dest=3, type="KNOWS", id=11),
        ),
        total_nodes=3,
        total_edges=2,
    )
    opts = GraphDisplayOptions(hidden_labels={"Person"})
    visible = filter_graph(model, opts)
    assert {n.id for n in visible.nodes} == {2}
    assert visible.edges == ()


def test_filter_multi_label_visible_if_any_label_shown():
    model = GraphViewModel(
        nodes=(_node(1, ("A", "B"), name="x"), _node(2, ("A",), name="y")),
        edges=(GraphEdge(src=1, dest=2, type="REL", id=1),),
    )
    opts = GraphDisplayOptions(hidden_labels={"A"})
    visible = filter_graph(model, opts)
    assert {n.id for n in visible.nodes} == {1}
    assert visible.edges == ()


def test_filter_unlabeled_nodes_always_visible():
    model = GraphViewModel(
        nodes=(_node(1, (), name="x"), _node(2, ("Person",), name="y")),
        edges=(),
    )
    opts = GraphDisplayOptions(hidden_labels={"Person"})
    visible = filter_graph(model, opts)
    assert {n.id for n in visible.nodes} == {1}


def test_sync_from_model_defaults_and_preserves():
    model = GraphViewModel(
        nodes=(
            _node(1, ("Person",), name="Ada", email="a@x"),
            _node(2, ("Movie",), title="Matrix"),
        ),
        edges=(),
    )
    opts = GraphDisplayOptions()
    opts.sync_from_model(model)
    assert opts.hidden_labels == set()
    assert opts.props_by_label["Person"] == ["name"]
    assert opts.props_by_label["Movie"] == ["title"]
    assert opts.show_id is True

    opts.hidden_labels.add("Movie")
    opts.props_by_label["Person"] = ["email"]
    opts.sync_from_model(model)
    assert "Movie" in opts.hidden_labels
    assert opts.props_by_label["Person"] == ["email"]


def test_props_for_node_union_capped_at_three():
    node = _node(1, ("Person", "Actor"), name="Ada", email="a", age=30, city="X")
    opts = GraphDisplayOptions(
        props_by_label={
            "Person": ["name", "email"],
            "Actor": ["age", "city"],
        }
    )
    keys = props_for_node(node, opts)
    assert len(keys) == 3
    assert keys == ("name", "email", "age")


def test_toggle_prop_fifo_max_three():
    opts = GraphDisplayOptions(props_by_label={"Person": ["a", "b", "c"]})
    toggle_prop(opts, "Person", "d")
    assert opts.props_by_label["Person"] == ["b", "c", "d"]
    toggle_prop(opts, "Person", "b")
    assert opts.props_by_label["Person"] == ["c", "d"]
