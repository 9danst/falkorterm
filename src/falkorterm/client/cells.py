from __future__ import annotations

from typing import Any

from falkorterm.client.models import CellValue


def _jsonable(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _endpoint_id(endpoint: Any) -> int | None:
    if endpoint is None:
        return None
    if isinstance(endpoint, bool):
        return None
    if isinstance(endpoint, int):
        return endpoint
    node_id = getattr(endpoint, "id", None)
    if isinstance(node_id, int) and not isinstance(node_id, bool):
        return node_id
    return None


def _resolve_list_attr(value: Any, name: str) -> list[Any] | None:
    attr = getattr(value, name, None)
    if attr is None:
        return None
    if callable(attr):
        attr = attr()
    if attr is None:
        return []
    return list(attr)


def _serialize_node_like(node: Any) -> dict[str, object]:
    labels = getattr(node, "labels", None) or []
    properties = getattr(node, "properties", None) or {}
    detail: dict[str, object] = {
        "kind": "node",
        "labels": [str(x) for x in labels],
        "properties": _jsonable(dict(properties)),
    }
    node_id = getattr(node, "id", None)
    if node_id is not None:
        detail["id"] = node_id
    return detail


def _serialize_edge_like(edge: Any) -> dict[str, object]:
    relationship_type = getattr(edge, "relation", None)
    if relationship_type is None and hasattr(edge, "type"):
        type_attr = getattr(edge, "type")
        if not callable(type_attr):
            relationship_type = type_attr
    rel_name = str(relationship_type) if relationship_type is not None else "REL"
    props = getattr(edge, "properties", None) or {}
    detail: dict[str, object] = {
        "kind": "edge",
        "type": rel_name,
        "properties": _jsonable(dict(props)),
    }
    edge_id = getattr(edge, "id", None)
    if edge_id is not None:
        detail["id"] = edge_id
    src = _endpoint_id(getattr(edge, "src_node", None))
    dest = _endpoint_id(getattr(edge, "dest_node", None))
    if src is not None:
        detail["src"] = src
    if dest is not None:
        detail["dest"] = dest
    return detail


def to_cell_value(value: Any) -> CellValue:
    if value is None:
        return CellValue(display="")
    if isinstance(value, CellValue):
        return value
    if isinstance(value, bool):
        return CellValue(display=str(value))
    if isinstance(value, (int, float)):
        return CellValue(display=str(value))
    if isinstance(value, str):
        return CellValue(display=value)

    labels = getattr(value, "labels", None)
    properties = getattr(value, "properties", None)
    nodes_attr = getattr(value, "nodes", None)
    # Path objects expose nodes/edges as methods; treat callable as path-like marker.
    is_path_like = nodes_attr is not None
    relationship_type = getattr(value, "relation", None)
    if relationship_type is None and hasattr(value, "type"):
        # Avoid calling methods named type; only use if non-callable.
        type_attr = getattr(value, "type")
        if not callable(type_attr):
            relationship_type = type_attr

    # Node-like: has labels + properties, and is not path-like
    if labels is not None and properties is not None and not is_path_like:
        label_list = [str(x) for x in (labels or [])]
        props = dict(properties) if properties else {}
        node_id = getattr(value, "id", None)
        label_txt = ":".join(label_list) if label_list else ""
        if label_txt:
            display = f"(:{label_txt})"
        else:
            display = "(node)"
        if node_id is not None:
            display = f"{display[:-1]} id={node_id})"
        detail: dict[str, object] = {
            "kind": "node",
            "labels": label_list,
            "properties": _jsonable(props),
        }
        if node_id is not None:
            detail["id"] = node_id
        return CellValue(display=display, detail=detail)

    # Edge-like
    if properties is not None and (
        relationship_type is not None
        or hasattr(value, "src_node")
        or hasattr(value, "dest_node")
    ):
        edge_detail = _serialize_edge_like(value)
        rel_name = str(edge_detail.get("type", "REL"))
        display = f"-[:{rel_name}]->"
        return CellValue(display=display, detail=edge_detail)

    # Path-like
    if is_path_like:
        node_list = _resolve_list_attr(value, "nodes") or []
        edge_list = _resolve_list_attr(value, "edges") or []
        display = f"<path {len(node_list)} nodes>"
        serialized_nodes: list[object] = []
        for n in node_list:
            if hasattr(n, "labels") and hasattr(n, "properties"):
                serialized_nodes.append(_serialize_node_like(n))
            else:
                serialized_nodes.append(_jsonable(n))
        serialized_edges = [_serialize_edge_like(e) for e in edge_list]
        return CellValue(
            display=display,
            detail={
                "kind": "path",
                "nodes": serialized_nodes,
                "edges": serialized_edges,
            },
        )

    if isinstance(value, dict):
        return CellValue(
            display=str(value),
            detail={"kind": "object", "value": _jsonable(value)},
        )

    if isinstance(value, (list, tuple)):
        return CellValue(
            display=str(value),
            detail={"kind": "list", "value": _jsonable(value)},
        )

    if properties is not None:
        props = dict(properties) if properties else {}
        return CellValue(
            display=str(value),
            detail={"kind": "entity", "properties": _jsonable(props)},
        )

    return CellValue(display=str(value))
