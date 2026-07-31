from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Literal

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import Footer, Header, Static

from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import (
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
)
from falkorterm.config import load_config
from falkorterm.export import ExportFormat, write_export
from falkorterm.history import HistoryStore
from falkorterm.profiles import ProfileStore
from falkorterm.screens.cell_detail import CellDetailScreen
from falkorterm.screens.confirm import ConfirmScreen
from falkorterm.screens.connection import ConnectionScreen
from falkorterm.screens.export_format import ExportFormatScreen
from falkorterm.widgets.context import ContextWidget, SchemaItemSelected
from falkorterm.widgets.query import QuerySubmitted, QueryWidget
from falkorterm.widgets.results import (
    CellInspectRequested,
    ResultsWidget,
    format_result_meta,
)
from falkorterm.write_guard import is_write_query

FALKORTERM_THEME = Theme(
    name="falkorterm",
    primary="#1A6B6B",
    secondary="#2A8F8F",
    accent="#3ECFCF",
    warning="#D4A017",
    error="#E05C5C",
    success="#3CB371",
    foreground="#D8E6E6",
    background="#0D1416",
    surface="#121C1F",
    panel="#162428",
    dark=True,
)


class StatusBar(Static):
    """Shows connection target, last query summary, and a run hint."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
    }
    """

    _HINT = "Ctrl+Enter run"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._connection: Literal["connected", "disconnected", "running"] = (
            "disconnected"
        )
        self._target = ""
        self._detail = ""

    def set_status(self, text: str) -> None:
        """Backward-compatible plain update (also used as full replace)."""
        self.update(text)

    def set_connection(
        self,
        state: Literal["connected", "disconnected", "running"],
        target: str,
        detail: str | None = None,
    ) -> None:
        self._connection = state
        self._target = target
        if detail is not None:
            self._detail = detail
        self._render_status()

    def set_detail(self, detail: str) -> None:
        self._detail = detail
        self._render_status()

    def _render_status(self) -> None:
        if self._connection == "connected":
            conn = "[green]● connected[/]"
        elif self._connection == "running":
            conn = "[yellow]… running[/]"
        else:
            conn = "[red]○ disconnected[/]"

        parts = [conn]
        if self._target:
            parts.append(self._target)
        mid = "  ".join(parts)
        segments = [mid]
        if self._detail:
            segments.append(self._detail)
        segments.append(self._HINT)
        self.update("  │  ".join(segments))


class FalkorTerm(App):
    """Main FalkorDB terminal client."""

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "FalkorTerm"
    BINDINGS = [
        Binding("ctrl+1", "focus_context", "Context"),
        Binding("ctrl+2", "focus_results", "Results"),
        Binding("ctrl+3", "focus_query", "Query"),
        # Many terminals send \\n (ctrl+j) for Ctrl+Enter; only Kitty-style
        # protocols emit the literal ctrl+enter key.
        Binding("ctrl+j,ctrl+enter", "run_query", "Run", priority=True),
        Binding("ctrl+o", "open_connection", "Connect"),
        Binding("ctrl+e", "export_results", "Export"),
        Binding("r", "refresh_schema", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        config: ConnectionConfig | None = None,
        client: FalkorClient | None = None,
        history_store: HistoryStore | None = None,
        profile_store: ProfileStore | None = None,
    ) -> None:
        super().__init__()
        self.config = config or load_config()
        self.client = client or FalkorClient()
        self.history_store = history_store or HistoryStore()
        self.profile_store = profile_store or ProfileStore()
        self._query_running = False
        self._query_generation = 0
        self._connection_ok = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            yield ContextWidget(id="context")
            with Vertical(id="right-pane"):
                yield ResultsWidget(id="results")
                yield QueryWidget(id="query")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(FALKORTERM_THEME)
        self.theme = "falkorterm"
        self.sub_title = self.config.display_target
        self.query_one("#status", StatusBar).set_connection(
            "disconnected", self.config.display_target, detail="opening…"
        )
        self._push_connection_screen(can_dismiss=False)

    def action_focus_context(self) -> None:
        self.query_one("#context", ContextWidget).focus()

    def action_focus_results(self) -> None:
        self.query_one("#results", ResultsWidget).focus()

    def action_focus_query(self) -> None:
        self.query_one("#query", QueryWidget).query_one("#cypher-input").focus()

    def action_run_query(self) -> None:
        self.query_one("#query", QueryWidget).submit()

    def action_open_connection(self) -> None:
        self._push_connection_screen(can_dismiss=self._connection_ok)

    def action_export_results(self) -> None:
        result = self.query_one("#results", ResultsWidget).last_result
        if result is None:
            self.notify("No results to export", severity="warning")
            return
        self.push_screen(ExportFormatScreen(), self._on_export_format)

    def _on_export_format(self, fmt: ExportFormat | None) -> None:
        if fmt is None:
            return
        result = self.query_one("#results", ResultsWidget).last_result
        if result is None:
            self.notify("No results to export", severity="warning")
            return
        try:
            path = write_export(result, fmt)
        except OSError as exc:
            self.notify(f"Export failed: {exc}", severity="error")
            return
        self.notify(f"Exported to {path}")

    def action_cancel_query(self) -> None:
        if not self._query_running:
            return
        self._query_generation += 1
        self._clear_running()
        try:
            self.client.abort_and_reconnect()
        except FalkorConnectionError as exc:
            self._connection_ok = False
            self.query_one("#status", StatusBar).set_connection(
                "disconnected",
                self.config.display_target,
                detail="cancelled · reconnect failed",
            )
            self.notify(f"Cancelled; reconnect failed: {exc}", severity="error")
            return
        self.query_one("#status", StatusBar).set_connection(
            "connected",
            self.config.display_target,
            detail="cancelled · reconnected",
        )

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key == "escape" and self._query_running:
            self.action_cancel_query()
            event.prevent_default()
            event.stop()

    def action_refresh_schema(self) -> None:
        if not self._connection_ok:
            self._push_connection_screen(can_dismiss=False)
            return
        self._load_schema()

    def on_query_submitted(self, event: QuerySubmitted) -> None:
        if self._query_running:
            return
        if not self.client.connected:
            self.query_one("#results", ResultsWidget).show_error(
                "Not connected. Press Ctrl+o to connect."
            )
            return
        cypher = event.cypher
        if is_write_query(cypher):
            self.push_screen(
                ConfirmScreen(
                    "Confirm write query",
                    "This query may modify the graph. Continue?",
                    confirm_label="Run",
                    cancel_label="Cancel",
                ),
                lambda confirmed, q=cypher: self._on_write_confirmed(confirmed, q),
            )
            return
        self._start_query(cypher)

    def _on_write_confirmed(self, confirmed: bool | None, cypher: str) -> None:
        if not confirmed:
            return
        self._start_query(cypher)

    def _start_query(self, cypher: str) -> None:
        if self._query_running:
            return
        if not self.client.connected:
            self.query_one("#results", ResultsWidget).show_error(
                "Not connected. Press Ctrl+o to connect."
            )
            return
        self._query_running = True
        self._query_generation += 1
        gen = self._query_generation
        self.query_one("#status", StatusBar).set_connection(
            "running", self.config.display_target, detail="…"
        )
        self.query_one("#query", QueryWidget).set_running(True)
        self.run_worker(
            lambda: self._execute_query(cypher, gen),
            exclusive=True,
            thread=True,
            name="run_query",
        )

    def on_schema_item_selected(self, event: SchemaItemSelected) -> None:
        query = self.query_one("#query", QueryWidget)
        if event.kind == "property":
            query.append_snippet(f"n.{event.name}")
            return
        if event.kind == "label":
            template = f"MATCH (n:{event.name}) RETURN n LIMIT 25"
        else:
            template = f"MATCH ()-[r:{event.name}]->() RETURN r LIMIT 25"
        query.insert_template(template)

    def on_cell_inspect_requested(self, event: CellInspectRequested) -> None:
        self.push_screen(CellDetailScreen(event.cell))

    def _push_connection_screen(self, *, can_dismiss: bool) -> None:
        screen = ConnectionScreen(
            self.config,
            self.client,
            can_dismiss=can_dismiss,
            profile_store=self.profile_store,
        )
        self.push_screen(screen, self._on_connection_result)

    def _on_connection_result(self, result: ConnectionConfig | None) -> None:
        if result is None:
            if not self._connection_ok:
                self._push_connection_screen(can_dismiss=False)
            return
        self.config = result
        self._connection_ok = True
        self.sub_title = result.display_target
        status = self.query_one("#status", StatusBar)
        status.set_connection("connected", result.display_target, detail="")
        self.query_one("#query", QueryWidget).configure_history(
            self.history_store, result.display_target
        )
        self._load_schema()

    def _load_schema(self) -> None:
        context = self.query_one("#context", ContextWidget)
        try:
            schema = self.client.get_schema()
            context.set_schema(schema)
            self.query_one("#query", QueryWidget).set_schema_tokens(
                schema.labels,
                schema.relations,
                schema.property_keys,
            )
            self.query_one("#status", StatusBar).set_connection(
                "connected", self.config.display_target
            )
        except (FalkorQueryError, FalkorConnectionError) as exc:
            self.notify(f"Schema refresh failed: {exc}", severity="error")
            # Keep previous schema in the widget.

    def _execute_query(self, cypher: str, generation: int) -> None:
        # Prefer a worker thread; UI updates must hop back to the app thread.
        try:
            result = self.client.run_query(cypher)
        except FalkorQueryError as exc:
            self._call_on_app_thread(
                self._on_query_error, generation, str(exc), False
            )
        except FalkorConnectionError as exc:
            self._call_on_app_thread(
                self._on_query_error, generation, str(exc), True
            )
        else:
            self._call_on_app_thread(self._on_query_success, generation, result)
        finally:
            self._call_on_app_thread(self._clear_running_if, generation)

    def _call_on_app_thread(self, callback: Callable[..., Any], *args: Any) -> None:
        if threading.get_ident() == self._thread_id:
            callback(*args)
        else:
            self.call_from_thread(callback, *args)

    def _on_query_success(self, generation: int, result) -> None:
        if generation != self._query_generation:
            return
        self.query_one("#results", ResultsWidget).show_result(result)
        self.query_one("#status", StatusBar).set_connection(
            "connected",
            self.config.display_target,
            detail=format_result_meta(result),
        )

    def _on_query_error(
        self, generation: int, message: str, connection_lost: bool
    ) -> None:
        if generation != self._query_generation:
            return
        self.query_one("#results", ResultsWidget).show_error(message)
        short = message.replace("\n", " ")[:60]
        if connection_lost:
            self._connection_ok = False
            self.query_one("#status", StatusBar).set_connection(
                "disconnected",
                self.config.display_target,
                detail=short,
            )
        else:
            self.query_one("#status", StatusBar).set_connection(
                "connected",
                self.config.display_target,
                detail=f"error: {short}",
            )

    def _clear_running_if(self, generation: int) -> None:
        if generation != self._query_generation:
            return
        self._clear_running()

    def _clear_running(self) -> None:
        self._query_running = False
        self.query_one("#query", QueryWidget).set_running(False)

    def _set_status(self, text: str) -> None:
        self.query_one("#status", StatusBar).set_status(text)


def run_app(config: ConnectionConfig | None = None) -> None:
    FalkorTerm(config=config).run()
