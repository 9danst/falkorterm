from __future__ import annotations

from typing import Literal

from textual.actions import SkipAction
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Collapsible, Label, ListItem, ListView, Static

from falkorterm.client.models import ConnectionConfig, GraphSchema

_LOGO_F = "███╗\n█╔═╝\n█║  "
_LOGO_T = "████╗\n╚═█╔╝\n  █║"


class SchemaItemSelected(Message):
    """Emitted when the user selects a label, relation, or property key."""

    def __init__(
        self,
        kind: Literal["label", "relation", "property"],
        name: str,
        *,
        action: Literal["match", "count"] = "match",
    ) -> None:
        super().__init__()
        self.kind = kind
        self.name = name
        self.action = action


class SchemaListItem(ListItem):
    """A schema row: name on the left, optional instance count on the right."""

    def __init__(
        self,
        kind: Literal["label", "relation", "property"],
        item_name: str,
        *,
        count: int | None = None,
    ) -> None:
        children: list[Label] = [Label(item_name, classes="schema-name")]
        if count is not None:
            children.append(Label(str(count), classes="schema-count"))
        super().__init__(Horizontal(*children, classes="schema-row"))
        self.kind = kind
        self.item_name = item_name


class ContextWidget(Static):
    """Sidebar listing graph labels, relationship types, and property keys."""

    BINDINGS = [
        Binding("c", "count_selected", "Count", show=False, priority=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Context"
        self.border_subtitle = "Enter match · c count"
        self._schema = GraphSchema(labels=(), relations=())
        self._config: ConnectionConfig | None = None

    def compose(self):
        with Vertical(id="context-logo"):
            with Horizontal(id="logo-letters"):
                yield Static(_LOGO_F, classes="logo-f")
                yield Static(_LOGO_T, classes="logo-t")
            yield Label("falkorTerm · 1.0", classes="logo-tagline")
        yield Static(id="graph-summary")
        with Collapsible(
            title="Labels · 0", id="labels-section", collapsed=False
        ):
            yield Label("No labels", id="labels-empty", classes="empty-state")
            yield ListView(id="labels-list")
        with Collapsible(
            title="Relations · 0", id="relations-section", collapsed=False
        ):
            yield Label("No relations", id="relations-empty", classes="empty-state")
            yield ListView(id="relations-list")
        with Collapsible(
            title="Properties · 0", id="properties-section", collapsed=False
        ):
            yield Label(
                "No properties", id="properties-empty", classes="empty-state"
            )
            yield ListView(id="properties-list")

    def on_mount(self) -> None:
        self.set_schema(self._schema)

    def set_connection(self, config: ConnectionConfig | None) -> None:
        self._config = config
        self._refresh_summary()

    def set_schema(self, schema: GraphSchema) -> None:
        self._schema = schema
        labels_list = self.query_one("#labels-list", ListView)
        relations_list = self.query_one("#relations-list", ListView)
        properties_list = self.query_one("#properties-list", ListView)
        labels_section = self.query_one("#labels-section", Collapsible)
        relations_section = self.query_one("#relations-section", Collapsible)
        properties_section = self.query_one("#properties-section", Collapsible)
        labels_empty = self.query_one("#labels-empty", Label)
        relations_empty = self.query_one("#relations-empty", Label)
        properties_empty = self.query_one("#properties-empty", Label)

        labels_list.clear()
        relations_list.clear()
        properties_list.clear()

        label_count_map = dict(schema.label_counts)
        relation_count_map = dict(schema.relation_counts)

        n_labels = len(schema.labels)
        n_relations = len(schema.relations)
        n_props = len(schema.property_keys)
        labels_section.title = f"Labels · {n_labels}"
        relations_section.title = f"Relations · {n_relations}"
        properties_section.title = f"Properties · {n_props}"

        labels_empty.display = n_labels == 0
        relations_empty.display = n_relations == 0
        properties_empty.display = n_props == 0
        labels_list.display = n_labels > 0
        relations_list.display = n_relations > 0
        properties_list.display = n_props > 0

        for name in schema.labels:
            count = label_count_map.get(name)
            labels_list.append(SchemaListItem("label", name, count=count))
        for name in schema.relations:
            count = relation_count_map.get(name)
            relations_list.append(SchemaListItem("relation", name, count=count))
        for name in schema.property_keys:
            properties_list.append(SchemaListItem("property", name))

        total = n_labels + n_relations + n_props
        self.border_title = f"Context · {total}"
        self.border_subtitle = "Enter match · c count"
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        summary = self.query_one("#graph-summary", Static)
        schema = self._schema
        n_labels = len(schema.labels)
        n_relations = len(schema.relations)
        n_props = len(schema.property_keys)
        nodes = sum(c for _, c in schema.label_counts)
        edges = sum(c for _, c in schema.relation_counts)

        if self._config is None:
            target = "Not connected"
        else:
            target = self._config.display_target

        lines = [
            f"[bold]{target}[/bold]",
            f"nodes ~{nodes} · edges {edges}",
            f"labels {n_labels} · rels {n_relations} · props {n_props}",
        ]
        if self._config is not None and self._config.read_only:
            lines.append("mode read-only")
        summary.update("\n".join(lines))

    def _focused_schema_item(self) -> SchemaListItem | None:
        for list_id in ("#labels-list", "#relations-list", "#properties-list"):
            list_view = self.query_one(list_id, ListView)
            if not list_view.has_focus:
                continue
            highlighted = list_view.highlighted_child
            if isinstance(highlighted, SchemaListItem):
                return highlighted
        return None

    def action_count_selected(self) -> None:
        item = self._focused_schema_item()
        if item is None or item.kind == "property":
            # Don't swallow `c` when count doesn't apply (e.g. graph copy).
            raise SkipAction()
        self.post_message(
            SchemaItemSelected(item.kind, item.item_name, action="count")
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, SchemaListItem):
            self.post_message(
                SchemaItemSelected(item.kind, item.item_name, action="match")
            )
