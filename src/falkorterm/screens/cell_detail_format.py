from __future__ import annotations

import json
from typing import TYPE_CHECKING

from falkorterm.client.models import CellValue

if TYPE_CHECKING:
    from textual.widgets import Tree


def format_cell_value(value: object) -> str:
    if value is None or isinstance(value, (str, int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _join_parts(parts: list[str]) -> str:
    return " · ".join(parts)


def _int_id(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def format_header_text(cell: CellValue) -> str:
    detail = cell.detail
    if detail is None:
        return cell.display

    kind = detail.get("kind")
    if kind == "node":
        parts = ["node"]
        node_id = _int_id(detail.get("id"))
        if node_id is not None:
            parts.append(f"id={node_id}")
        labels = detail.get("labels")
        if isinstance(labels, list) and labels:
            parts.append("labels " + ":".join(str(label) for label in labels))
        return _join_parts(parts)

    if kind == "edge":
        parts = ["edge"]
        edge_id = _int_id(detail.get("id"))
        if edge_id is not None:
            parts.append(f"id={edge_id}")
        edge_type = detail.get("type")
        if edge_type is not None:
            parts.append(str(edge_type))
        src = _int_id(detail.get("src"))
        dest = _int_id(detail.get("dest"))
        if src is not None and dest is not None:
            parts.append(f"{src}→{dest}")
        return _join_parts(parts)

    if kind == "path":
        nodes = detail.get("nodes")
        edges = detail.get("edges")
        node_count = len(nodes) if isinstance(nodes, list) else 0
        edge_count = len(edges) if isinstance(edges, list) else 0
        return _join_parts(["path", f"{node_count} nodes", f"{edge_count} edges"])

    if kind == "object":
        value = detail.get("value")
        key_count = len(value) if isinstance(value, dict) else 0
        return f"object · {key_count} keys"

    if kind == "list":
        value = detail.get("value")
        item_count = len(value) if isinstance(value, list) else 0
        return f"list · {item_count} items"

    if kind == "entity":
        return "entity"

    return cell.display


def _format_node_short(node: object) -> str:
    if not isinstance(node, dict):
        return format_cell_value(node)
    labels = node.get("labels")
    label_txt = ""
    if isinstance(labels, list) and labels:
        label_txt = ":".join(str(label) for label in labels)
    if label_txt:
        display = f"(:{label_txt})"
    else:
        display = "(node)"
    node_id = _int_id(node.get("id"))
    if node_id is not None:
        display = f"{display[:-1]} id={node_id})"
    return display


def _format_edge_short(edge: object) -> str:
    if not isinstance(edge, dict):
        return format_cell_value(edge)
    edge_type = edge.get("type")
    rel_name = str(edge_type) if edge_type is not None else "REL"
    edge_id = _int_id(edge.get("id"))
    if edge_id is not None:
        display = f"-[:{rel_name} id={edge_id}]->"
    else:
        display = f"-[:{rel_name}]->"
    src = _int_id(edge.get("src"))
    dest = _int_id(edge.get("dest"))
    if src is not None and dest is not None:
        display = f"{display} {src}→{dest}"
    return display


def _rows_from_mapping(mapping: object) -> list[tuple[str, str]]:
    if not isinstance(mapping, dict) or not mapping:
        return [("(no properties)", "")]
    return [(str(key), format_cell_value(value)) for key, value in mapping.items()]


def iter_property_rows(cell: CellValue) -> list[tuple[str, str]]:
    detail = cell.detail
    if detail is None:
        return [("(no properties)", "")]

    kind = detail.get("kind")
    if kind in {"node", "edge", "entity"}:
        return _rows_from_mapping(detail.get("properties"))

    if kind == "path":
        rows: list[tuple[str, str]] = []
        nodes = detail.get("nodes")
        if isinstance(nodes, list):
            for index, node in enumerate(nodes):
                rows.append((f"nodes[{index}]", _format_node_short(node)))
        edges = detail.get("edges")
        if isinstance(edges, list):
            for index, edge in enumerate(edges):
                rows.append((f"edges[{index}]", _format_edge_short(edge)))
        return rows or [("(no properties)", "")]

    if kind == "object":
        value = detail.get("value")
        if isinstance(value, dict):
            return _rows_from_mapping(value)
        return [("value", format_cell_value(value))]

    if kind == "list":
        value = detail.get("value")
        if isinstance(value, list):
            if not value:
                return [("(no properties)", "")]
            return [(f"[{index}]", format_cell_value(item)) for index, item in enumerate(value)]
        return [("value", format_cell_value(value))]

    return [("(no properties)", "")]


def _populate_tree_node(node: object, data: object) -> None:
    from textual.widgets._tree import TreeNode

    if not isinstance(node, TreeNode):
        return

    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key)
            if isinstance(value, (dict, list)):
                child = node.add(key_text)
                _populate_tree_node(child, value)
            else:
                node.add(f"{key_text}: {format_cell_value(value)}")
        return

    if isinstance(data, list):
        for index, value in enumerate(data):
            label = f"[{index}]"
            if isinstance(value, (dict, list)):
                child = node.add(label)
                _populate_tree_node(child, value)
            else:
                node.add(f"{label}: {format_cell_value(value)}")
        return

    node.label = format_cell_value(data)


def add_json_to_tree(tree: Tree[str], data: object) -> None:
    tree.root.expand()
    _populate_tree_node(tree.root, data)
