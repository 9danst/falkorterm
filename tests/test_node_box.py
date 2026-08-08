from falkorterm.graph.display import GraphDisplayOptions, fit_line
from falkorterm.graph.models import GraphNode
from falkorterm.graph.node_box import (
    MAX_INNER_SELECTED,
    MAX_INNER_UNSELECTED,
    inner_parts_for_node,
)


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


def test_fit_line_truncates_long_text():
    assert fit_line("abcdefghij", 8) == "abcdefg…"


def test_fit_line_leaves_short_text():
    assert fit_line("abc", 8) == "abc"


def test_inner_parts_truncates_long_label():
    node = _node(1, ("VeryLongLabelNameThatExceeds",))
    parts = inner_parts_for_node(node, None, selected=False)
    assert parts[0] == fit_line(":VeryLongLabelNameThatExceeds", MAX_INNER_UNSELECTED)
    assert len(parts[0]) <= MAX_INNER_UNSELECTED


def test_inner_parts_name_prop_value_only():
    node = _node(1, ("Person",), name="Ada")
    opts = GraphDisplayOptions(props_by_label={"Person": ["name"]}, show_id=False)
    parts = inner_parts_for_node(node, opts, selected=False)
    assert "name=" not in " ".join(parts)
    assert "Ada" in parts


def test_inner_parts_non_auto_prop_uses_key_equals():
    node = _node(1, ("Person",), email="a@example.com")
    opts = GraphDisplayOptions(props_by_label={"Person": ["email"]}, show_id=False)
    parts = inner_parts_for_node(node, opts, selected=False)
    assert any("email=a@example.com" in part for part in parts)


def test_inner_parts_selected_allows_wider_budget():
    long_label = "X" * 30
    node = _node(1, (long_label,))
    unselected = inner_parts_for_node(node, None, selected=False)
    selected = inner_parts_for_node(node, None, selected=True)
    assert len(unselected[0]) <= MAX_INNER_UNSELECTED
    assert len(selected[0]) <= MAX_INNER_SELECTED
    assert len(selected[0]) > len(unselected[0])


def test_inner_parts_legacy_auto_prop_when_display_none():
    node = _node(1, ("Person",), name="Ada Lovelace", city="London")
    parts = inner_parts_for_node(node, None, selected=False)
    assert parts[0] == ":Person"
    assert "id=1" in parts
    assert "Ada Lovelace" in parts
    assert "city=" not in " ".join(parts)
