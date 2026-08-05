from falkorterm.client.models import ConnectionConfig, GraphSchema
from falkorterm.widgets.context import ContextWidget, SchemaItemSelected
from falkorterm.widgets.query import QueryWidget
from textual.app import App, ComposeResult
from textual.widgets import Collapsible, Label, Static


class ContextHarness(App):
    def compose(self) -> ComposeResult:
        yield ContextWidget(id="context")
        yield QueryWidget(id="query")

    def on_schema_item_selected(self, event: SchemaItemSelected) -> None:
        self.selected = (event.kind, event.name, event.action)
        if event.action == "count":
            if event.kind == "label":
                template = f"MATCH (n:{event.name}) RETURN count(n) AS count"
            else:
                template = f"MATCH ()-[r:{event.name}]->() RETURN count(r) AS count"
        elif event.kind == "label":
            template = f"MATCH (n:{event.name}) RETURN n LIMIT 25"
        elif event.kind == "relation":
            template = f"MATCH ()-[r:{event.name}]->() RETURN r LIMIT 25"
        else:
            return
        self.query_one("#query", QueryWidget).insert_template(template)


def _item_name_and_count(item) -> tuple[str, str | None]:
    name = str(item.query_one(".schema-name", Label).content)
    count_labels = item.query(".schema-count")
    if not count_labels:
        return name, None
    return name, str(count_labels.first().content)


def _summary_text(context: ContextWidget) -> str:
    return str(context.query_one("#graph-summary", Static).content)


async def test_context_logo_and_default_summary():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        await pilot.pause()
        assert context.query_one(".logo-f", Static)
        assert context.query_one(".logo-t", Static)
        tagline = str(context.query_one(".logo-tagline", Label).content)
        assert "falkorTerm" in tagline
        assert "1.0" in tagline
        summary = _summary_text(context)
        assert "Not connected" in summary
        assert "nodes ~0" in summary
        assert "edges 0" in summary


async def test_context_graph_summary_with_connection():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_connection(
            ConnectionConfig(host="localhost", port=6379, graph="aviation")
        )
        context.set_schema(
            GraphSchema(
                labels=("Person", "City"),
                relations=("KNOWS",),
                property_keys=("name", "age"),
                label_counts=(("Person", 40), ("City", 2)),
                relation_counts=(("KNOWS", 17),),
            )
        )
        await pilot.pause()
        summary = _summary_text(context)
        assert "aviation@localhost:6379" in summary
        assert "nodes ~42" in summary
        assert "edges 17" in summary
        assert "labels 2" in summary
        assert "rels 1" in summary
        assert "props 2" in summary
        assert "read-only" not in summary

        context.set_connection(
            ConnectionConfig(
                host="localhost", port=6379, graph="aviation", read_only=True
            )
        )
        await pilot.pause()
        assert "mode read-only" in _summary_text(context)


async def test_context_set_schema_and_select_label():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_schema(
            GraphSchema(
                labels=("Person",),
                relations=("KNOWS",),
                label_counts=(("Person", 3),),
            )
        )
        await pilot.pause()
        labels = context.query_one("#labels-list")
        assert len(labels.children) == 1
        name, count = _item_name_and_count(labels.children[0])
        assert name == "Person"
        assert count == "3"
        assert "(n)" not in name
        labels_section = context.query_one("#labels-section", Collapsible)
        assert labels_section.title == "Labels · 1"
        rel_section = context.query_one("#relations-section", Collapsible)
        assert rel_section.title == "Relations · 1"
        assert context.border_title == "Context · 2"
        assert not context.query_one("#labels-empty").display
        context.post_message(SchemaItemSelected("label", "Person"))
        await pilot.pause()
        assert app.selected == ("label", "Person", "match")
        assert "Person" in app.query_one("#query", QueryWidget).get_text()
        assert "LIMIT 25" in app.query_one("#query", QueryWidget).get_text()


async def test_context_count_action():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_schema(GraphSchema(labels=("Person",), relations=("KNOWS",)))
        await pilot.pause()
        context.post_message(
            SchemaItemSelected("label", "Person", action="count")
        )
        await pilot.pause()
        assert app.selected == ("label", "Person", "count")
        text = app.query_one("#query", QueryWidget).get_text()
        assert "count(n)" in text
        context.post_message(
            SchemaItemSelected("relation", "KNOWS", action="count")
        )
        await pilot.pause()
        assert "count(r)" in app.query_one("#query", QueryWidget).get_text()


async def test_context_empty_schema_shows_empty_states():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        context.set_schema(GraphSchema(labels=(), relations=()))
        await pilot.pause()
        assert context.query_one("#labels-empty").display
        assert context.query_one("#relations-empty").display
        assert context.query_one("#properties-empty").display
        assert not context.query_one("#labels-list").display
        assert context.border_title == "Context · 0"
        assert context.query_one("#labels-section", Collapsible).title == "Labels · 0"
        summary = _summary_text(context)
        assert "Not connected" in summary
        assert "nodes ~0" in summary


async def test_context_sections_expanded_by_default():
    app = ContextHarness()
    async with app.run_test() as pilot:
        context = app.query_one("#context", ContextWidget)
        await pilot.pause()
        assert not context.query_one("#labels-section", Collapsible).collapsed
        assert not context.query_one("#relations-section", Collapsible).collapsed
        assert not context.query_one("#properties-section", Collapsible).collapsed
