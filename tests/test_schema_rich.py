from types import SimpleNamespace
from unittest.mock import MagicMock

from falkorterm.client.cells import to_cell_value
from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import ConnectionConfig, GraphSchema
from textual.app import App, ComposeResult
from textual.widgets import Label

from falkorterm.widgets.context import ContextWidget, SchemaItemSelected
from falkorterm.widgets.query import QueryWidget


def _make_raw(header, rows):
    return SimpleNamespace(header=header, result_set=rows)


def test_get_schema_degrades_when_counts_fail():
    client = FalkorClient()
    client._graph = MagicMock()
    client._config = ConnectionConfig()
    client._db = MagicMock()

    def query_side_effect(cypher, timeout=None):
        if "labels()" in cypher:
            return _make_raw(["label"], [["Person"]])
        if "relationshipTypes" in cypher:
            return _make_raw(["rel"], [["KNOWS"]])
        if "propertyKeys" in cypher:
            return _make_raw(["key"], [["name"]])
        if "UNWIND" in cypher or "type(r)" in cypher:
            raise RuntimeError("count failed")
        raise AssertionError(cypher)

    client._graph.query.side_effect = query_side_effect
    schema = client.get_schema()
    assert schema.labels == ("Person",)
    assert schema.property_keys == ("name",)
    assert schema.label_counts == (("Person", 0),)
    assert schema.relation_counts == (("KNOWS", 0),)


class SchemaHarness(App):
    def compose(self) -> ComposeResult:
        yield ContextWidget(id="context")
        yield QueryWidget(id="query")

    def on_schema_item_selected(self, event: SchemaItemSelected) -> None:
        self.selected = (event.kind, event.name)
        if event.kind == "property":
            self.query_one("#query", QueryWidget).append_snippet(f"n.{event.name}")


async def test_context_shows_counts_and_properties():
    app = SchemaHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_schema(
            GraphSchema(
                labels=("Person",),
                relations=("KNOWS",),
                property_keys=("name",),
                label_counts=(("Person", 42),),
                relation_counts=(("KNOWS", 10),),
            )
        )
        await pilot.pause()
        labels = context.query_one("#labels-list")
        item = labels.children[0]
        assert str(item.query_one(".schema-name", Label).content) == "Person"
        assert str(item.query_one(".schema-count", Label).content) == "42"
        props = context.query_one("#properties-list")
        assert len(props.children) == 1
        prop = props.children[0]
        assert str(prop.query_one(".schema-name", Label).content) == "name"
        assert list(prop.query(".schema-count")) == []
        from textual.widgets import Collapsible

        assert context.query_one("#properties-section", Collapsible).title == (
            "Properties · 1"
        )
        assert context.border_title == "Context · 3"
        context.post_message(SchemaItemSelected("property", "name"))
        await pilot.pause()
        assert app.selected == ("property", "name")
        assert "n.name" in app.query_one("#query", QueryWidget).get_text()


def test_to_cell_value_node():
    node = SimpleNamespace(labels=["Person"], properties={"name": "Ada"}, id=1)
    cell = to_cell_value(node)
    assert "Person" in cell.display
    assert cell.detail is not None
    assert cell.detail["kind"] == "node"
