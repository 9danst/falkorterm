from __future__ import annotations

from typing import Literal

from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from falkorterm.client.models import GraphSchema


class SchemaItemSelected(Message):
    """Emitted when the user selects a label or relation in the sidebar."""

    def __init__(self, kind: Literal["label", "relation"], name: str) -> None:
        super().__init__()
        self.kind = kind
        self.name = name


class SchemaListItem(ListItem):
    def __init__(self, kind: Literal["label", "relation"], item_name: str) -> None:
        super().__init__(Label(item_name))
        self.kind = kind
        self.item_name = item_name


class ContextWidget(Static):
    """Sidebar listing graph labels and relationship types."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Context"
        self._schema = GraphSchema(labels=(), relations=())

    def compose(self):
        yield Label("Labels")
        yield ListView(id="labels-list")
        yield Label("Relations")
        yield ListView(id="relations-list")

    def set_schema(self, schema: GraphSchema) -> None:
        self._schema = schema
        labels_list = self.query_one("#labels-list", ListView)
        relations_list = self.query_one("#relations-list", ListView)
        labels_list.clear()
        relations_list.clear()
        for name in schema.labels:
            labels_list.append(SchemaListItem("label", name))
        for name in schema.relations:
            relations_list.append(SchemaListItem("relation", name))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, SchemaListItem):
            self.post_message(SchemaItemSelected(item.kind, item.item_name))
