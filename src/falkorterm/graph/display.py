from __future__ import annotations

from dataclasses import dataclass, field

from falkorterm.graph.models import GraphNode, GraphViewModel

_AUTO_PROP_KEYS = ("name", "title", "label")
_MAX_PROPS = 3


def _auto_prop_key(properties: dict[str, object]) -> str | None:
    for key in _AUTO_PROP_KEYS:
        if key in properties and properties[key] is not None:
            return key
    for key, value in properties.items():
        if value is not None:
            return key
    return None


def _keys_for_label(model: GraphViewModel, label: str) -> set[str]:
    keys: set[str] = set()
    for node in model.nodes:
        if label in node.labels:
            keys.update(k for k, v in node.properties.items() if v is not None)
    return keys


@dataclass
class GraphDisplayOptions:
    hidden_labels: set[str] = field(default_factory=set)
    props_by_label: dict[str, list[str]] = field(default_factory=dict)
    show_id: bool = True
    active_label: str | None = None
    known_keys_by_label: dict[str, set[str]] = field(default_factory=dict)

    def sync_from_model(self, model: GraphViewModel) -> None:
        labels: set[str] = set()
        for node in model.nodes:
            labels.update(node.labels)

        for label in sorted(labels):
            keys = _keys_for_label(model, label)
            self.known_keys_by_label[label] = keys
            if label not in self.props_by_label:
                # Prefer auto key from any node of this label.
                auto: str | None = None
                for node in model.nodes:
                    if label in node.labels:
                        auto = _auto_prop_key(node.properties)
                        if auto is not None:
                            break
                self.props_by_label[label] = [auto] if auto else []

        if self.active_label is None or self.active_label not in labels:
            self.active_label = next(iter(sorted(labels)), None)

        # Drop hidden flags for labels that vanished? Keep them so they re-apply
        # if the label returns; sync does not clear hidden_labels.


def node_is_visible(node: GraphNode, opts: GraphDisplayOptions) -> bool:
    if not node.labels:
        return True
    return any(label not in opts.hidden_labels for label in node.labels)


def filter_graph(model: GraphViewModel, opts: GraphDisplayOptions) -> GraphViewModel:
    visible_nodes = tuple(n for n in model.nodes if node_is_visible(n, opts))
    visible_ids = {n.id for n in visible_nodes}
    visible_edges = tuple(
        e for e in model.edges if e.src in visible_ids and e.dest in visible_ids
    )
    return GraphViewModel(
        nodes=visible_nodes,
        edges=visible_edges,
        truncated=model.truncated,
        total_nodes=len(visible_nodes),
        total_edges=len(visible_edges),
    )


def props_for_node(node: GraphNode, opts: GraphDisplayOptions) -> tuple[str, ...]:
    seen: list[str] = []
    for label in node.labels:
        for key in opts.props_by_label.get(label, ()):
            if key in node.properties and node.properties[key] is not None:
                if key not in seen:
                    seen.append(key)
            if len(seen) >= _MAX_PROPS:
                return tuple(seen)
    return tuple(seen)


def toggle_prop(opts: GraphDisplayOptions, label: str, key: str) -> None:
    current = list(opts.props_by_label.get(label, []))
    if key in current:
        current.remove(key)
    else:
        current.append(key)
        while len(current) > _MAX_PROPS:
            current.pop(0)
    opts.props_by_label[label] = current


def format_prop_line(key: str, value: object, *, max_len: int = 16) -> str:
    text = f"{key}={value}".replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text
