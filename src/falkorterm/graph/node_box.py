from __future__ import annotations

from falkorterm.graph.display import GraphDisplayOptions, fit_line, props_for_node
from falkorterm.graph.models import GraphNode

MAX_INNER_UNSELECTED = 24
MAX_INNER_SELECTED = 32

_AUTO_PROP_KEYS = frozenset({"name", "title", "label"})
_LEGACY_SKIP_KEYS = frozenset({"name", "title", "id", "label"})


def _budget(*, selected: bool) -> int:
    return MAX_INNER_SELECTED if selected else MAX_INNER_UNSELECTED


def _label_line(node: GraphNode, max_len: int) -> str:
    label = f":{':'.join(node.labels)}" if node.labels else "node"
    return fit_line(label, max_len)


def _legacy_auto_prop(node: GraphNode, max_len: int) -> str | None:
    props = node.properties
    for key in ("name", "title", "label"):
        if key in props and props[key] is not None:
            text = str(props[key]).replace("\n", " ")
            return fit_line(text, max_len)
    for key, value in props.items():
        if key in _LEGACY_SKIP_KEYS or value is None:
            continue
        text = str(value).replace("\n", " ")
        return fit_line(text, max_len)
    return None


def _format_prop(key: str, value: object, max_len: int) -> str:
    text = str(value).replace("\n", " ")
    if key in _AUTO_PROP_KEYS:
        return fit_line(text, max_len)
    return fit_line(f"{key}={value}".replace("\n", " "), max_len)


def inner_parts_for_node(
    node: GraphNode,
    display: GraphDisplayOptions | None,
    *,
    selected: bool = False,
) -> list[str]:
    max_len = _budget(selected=selected)
    parts: list[str] = [_label_line(node, max_len)]

    if display is None or display.show_id:
        parts.append(fit_line(f"id={node.id}", max_len))

    if display is None:
        prop = _legacy_auto_prop(node, max_len)
        if prop:
            parts.append(prop)
        return parts

    for key in props_for_node(node, display):
        value = node.properties.get(key)
        if value is not None:
            parts.append(_format_prop(key, value, max_len))
    return parts
