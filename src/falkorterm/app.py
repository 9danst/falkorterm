from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import (
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
    GraphSchema,
)
from falkorterm.config import load_config
from falkorterm.widgets.context import ContextWidget, SchemaItemSelected
from falkorterm.widgets.query import QuerySubmitted, QueryWidget
from falkorterm.widgets.results import ResultsWidget


class StatusBar(Static):
    """Shows connection target and status in the footer area."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def set_status(self, text: str) -> None:
        self.update(text)


class FalkorTerm(App):
    """Main FalkorDB terminal client."""

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "FalkorTerm"
    BINDINGS = [
        ("ctrl+1", "focus_context", "Context"),
        ("ctrl+2", "focus_results", "Results"),
        ("ctrl+3", "focus_query", "Query"),
        ("ctrl+enter", "run_query", "Run"),
        ("r", "refresh_schema", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        config: ConnectionConfig | None = None,
        client: FalkorClient | None = None,
    ) -> None:
        super().__init__()
        self.config = config or load_config()
        self.client = client or FalkorClient()
        self._query_running = False
        self._connection_ok = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield ContextWidget(id="context")
            with Vertical(id="right-pane"):
                yield ResultsWidget(id="results")
                yield QueryWidget(id="query")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._connect_and_load_schema()

    def action_focus_context(self) -> None:
        self.query_one("#context", ContextWidget).focus()

    def action_focus_results(self) -> None:
        self.query_one("#results", ResultsWidget).focus()

    def action_focus_query(self) -> None:
        self.query_one("#query", QueryWidget).query_one("#cypher-input").focus()

    def action_run_query(self) -> None:
        self.query_one("#query", QueryWidget).submit()

    def action_refresh_schema(self) -> None:
        if not self._connection_ok:
            self._connect_and_load_schema()
            return
        self._load_schema()

    def on_query_submitted(self, event: QuerySubmitted) -> None:
        if self._query_running:
            return
        if not self.client.connected:
            self.query_one("#results", ResultsWidget).show_error(
                "Not connected. Press r to reconnect."
            )
            return
        self._query_running = True
        self._set_status("Running…")
        self.run_worker(
            self._execute_query(event.cypher),
            exclusive=True,
            thread=True,
            name="run_query",
        )

    def on_schema_item_selected(self, event: SchemaItemSelected) -> None:
        if event.kind == "label":
            template = f"MATCH (n:{event.name}) RETURN n LIMIT 25"
        else:
            template = f"MATCH ()-[r:{event.name}]->() RETURN r LIMIT 25"
        query = self.query_one("#query", QueryWidget)
        query.insert_template(template)

    def _connect_and_load_schema(self) -> None:
        status = self.query_one("#status", StatusBar)
        results = self.query_one("#results", ResultsWidget)
        try:
            self.client.connect(self.config)
            self._connection_ok = True
            status.set_status(f"connected — {self.config.display_target}")
            self._load_schema()
        except FalkorConnectionError as exc:
            self._connection_ok = False
            status.set_status(f"error — {self.config.display_target}")
            results.show_error(f"Connection failed: {exc}")

    def _load_schema(self) -> None:
        context = self.query_one("#context", ContextWidget)
        try:
            schema = self.client.get_schema()
            context.set_schema(schema)
            self._set_status(f"connected — {self.config.display_target}")
        except (FalkorQueryError, FalkorConnectionError) as exc:
            self.notify(f"Schema refresh failed: {exc}", severity="error")
            # Keep previous schema in the widget.

    def _execute_query(self, cypher: str) -> None:
        # Runs in a worker thread — only touch the client here; UI via call_from_thread.
        try:
            result = self.client.run_query(cypher)
        except FalkorQueryError as exc:
            self.call_from_thread(self._on_query_error, str(exc), False)
        except FalkorConnectionError as exc:
            self.call_from_thread(self._on_query_error, str(exc), True)
        else:
            self.call_from_thread(self._on_query_success, result)
        finally:
            self.call_from_thread(self._clear_running)

    def _on_query_success(self, result) -> None:
        self.query_one("#results", ResultsWidget).show_result(result)
        self._set_status(f"connected — {self.config.display_target}")

    def _on_query_error(self, message: str, connection_lost: bool) -> None:
        self.query_one("#results", ResultsWidget).show_error(message)
        if connection_lost:
            self._connection_ok = False
            self._set_status(f"error — {self.config.display_target}")
        else:
            self._set_status(f"connected — {self.config.display_target}")

    def _clear_running(self) -> None:
        self._query_running = False

    def _set_status(self, text: str) -> None:
        self.query_one("#status", StatusBar).set_status(text)


def run_app(config: ConnectionConfig | None = None) -> None:
    FalkorTerm(config=config).run()
