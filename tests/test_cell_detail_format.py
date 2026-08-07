from __future__ import annotations

from textual.widgets import Tree

from falkorterm.client.models import CellValue
from falkorterm.screens.cell_detail_format import (
    add_json_to_tree,
    format_cell_value,
    format_header_text,
    iter_property_rows,
)


def test_format_header_node():
    cell = CellValue(
        display="(:Person id=7)",
        detail={"kind": "node", "id": 7, "labels": ["Person", "Dev"], "properties": {}},
    )
    assert format_header_text(cell) == "node · id=7 · labels Person:Dev"


def test_format_header_edge():
    cell = CellValue(
        display="-[:KNOWS]->",
        detail={
            "kind": "edge",
            "id": 9,
            "type": "KNOWS",
            "src": 1,
            "dest": 2,
            "properties": {},
        },
    )
    assert format_header_text(cell) == "edge · id=9 · KNOWS · 1→2"


def test_format_header_path():
    cell = CellValue(
        display="<path>",
        detail={"kind": "path", "nodes": [{}, {}], "edges": [{}]},
    )
    assert format_header_text(cell) == "path · 2 nodes · 1 edges"


def test_format_header_object_and_list():
    assert (
        format_header_text(
            CellValue(display="{}", detail={"kind": "object", "value": {"a": 1, "b": 2}})
        )
        == "object · 2 keys"
    )
    assert (
        format_header_text(
            CellValue(display="[]", detail={"kind": "list", "value": [1, 2, 3]})
        )
        == "list · 3 items"
    )


def test_format_header_entity_and_no_detail():
    assert format_header_text(
        CellValue(display="x", detail={"kind": "entity", "properties": {}})
    ) == "entity"
    assert format_header_text(CellValue(display="hello")) == "hello"


def test_format_cell_value_nested_one_line():
    assert format_cell_value({"a": 1}) == '{"a": 1}'
    assert format_cell_value([1, 2]) == "[1, 2]"
    assert format_cell_value("x") == "x"
    assert format_cell_value(42) == "42"


def test_iter_property_rows_node():
    cell = CellValue(
        display="(:Person)",
        detail={
            "kind": "node",
            "properties": {"name": "Ada", "meta": {"x": 1}},
        },
    )
    rows = iter_property_rows(cell)
    assert rows == [("name", "Ada"), ("meta", '{"x": 1}')]


def test_iter_property_rows_empty():
    cell = CellValue(
        display="(:Person)",
        detail={"kind": "node", "properties": {}},
    )
    assert iter_property_rows(cell) == [("(no properties)", "")]


def test_iter_property_rows_path():
    cell = CellValue(
        display="<path>",
        detail={
            "kind": "path",
            "nodes": [
                {"kind": "node", "id": 1, "labels": ["Person"], "properties": {}},
                {"kind": "node", "labels": [], "properties": {}},
            ],
            "edges": [
                {
                    "kind": "edge",
                    "type": "KNOWS",
                    "id": 9,
                    "src": 1,
                    "dest": 2,
                    "properties": {},
                }
            ],
        },
    )
    rows = iter_property_rows(cell)
    assert rows[0] == ("nodes[0]", "(:Person id=1)")
    assert rows[1] == ("nodes[1]", "(node)")
    assert rows[2] == ("edges[0]", "-[:KNOWS id=9]-> 1→2")


def test_iter_property_rows_object_and_list():
    object_cell = CellValue(
        display="{}",
        detail={"kind": "object", "value": {"a": 1, "nested": [1, 2]}},
    )
    assert iter_property_rows(object_cell) == [
        ("a", "1"),
        ("nested", "[1, 2]"),
    ]

    list_cell = CellValue(
        display="[]",
        detail={"kind": "list", "value": ["x", {"y": 2}]},
    )
    assert iter_property_rows(list_cell) == [
        ("[0]", "x"),
        ("[1]", '{"y": 2}'),
    ]


def test_iter_property_rows_no_detail():
    assert iter_property_rows(CellValue(display="hello")) == [("(no properties)", "")]


def test_add_json_to_tree_expands_root():
    tree = Tree("detail")
    add_json_to_tree(tree, {"kind": "node", "properties": {"a": 1}})
    assert tree.root.is_expanded
    labels = [str(child.label) for child in tree.root.children]
    assert "kind: node" in labels
    assert "properties" in labels
    props = next(c for c in tree.root.children if str(c.label) == "properties")
    assert not props.is_expanded
    prop_labels = [str(c.label) for c in props.children]
    assert "a: 1" in prop_labels
