from textual.app import App, ComposeResult

from falkorterm.client.models import GraphSchema
from falkorterm.widgets.context import ContextWidget, SchemaItemSelected
from falkorterm.widgets.query import QueryWidget


class ContextHarness(App):
    def compose(self) -> ComposeResult:
        yield ContextWidget(id="context")
        yield QueryWidget(id="query")

    def on_schema_item_selected(self, event: SchemaItemSelected) -> None:
        self.selected = (event.kind, event.name)
        if event.kind == "label":
            template = f"MATCH (n:{event.name}) RETURN n LIMIT 25"
        else:
            template = f"MATCH ()-[r:{event.name}]->() RETURN r LIMIT 25"
        self.query_one("#query", QueryWidget).insert_template(template)


async def test_context_set_schema_and_select_label():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_schema(
            GraphSchema(labels=("Person",), relations=("KNOWS",))
        )
        await pilot.pause()
        labels = context.query_one("#labels-list")
        assert len(labels.children) == 1
        # Post selection directly to exercise the message path.
        from falkorterm.widgets.context import SchemaItemSelected

        context.post_message(SchemaItemSelected("label", "Person"))
        await pilot.pause()
        assert app.selected == ("label", "Person")
        assert "Person" in app.query_one("#query", QueryWidget).get_text()
        assert "LIMIT 25" in app.query_one("#query", QueryWidget).get_text()
