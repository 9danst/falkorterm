from __future__ import annotations

from dataclasses import replace

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import ConnectionConfig, FalkorConnectionError
from falkorterm.profiles import Profile, ProfileStore


class ConnectionScreen(ModalScreen[ConnectionConfig | None]):
    """Collect host/port/password/graph and open a FalkorDB connection."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(
        self,
        config: ConnectionConfig,
        client: FalkorClient,
        *,
        can_dismiss: bool = False,
        profile_store: ProfileStore | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._initial = config
        self._client = client
        self._can_dismiss = can_dismiss
        self._profile_store = profile_store or ProfileStore()
        self._graphs: list[str] = []
        self._applying_profile = False

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-dialog"):
            yield Label("Connect to FalkorDB", id="connection-title")
            yield Label("Profile")
            yield Select(
                [("— none —", Select.BLANK)],
                id="conn-profile-select",
                prompt="Saved profiles",
                allow_blank=True,
            )
            yield Label("Profile name")
            yield Input(
                value="",
                id="conn-profile-name",
                placeholder="e.g. local",
            )
            yield Label("Host")
            yield Input(
                value=self._initial.host,
                id="conn-host",
                placeholder="localhost",
            )
            yield Label("Port")
            yield Input(
                value=str(self._initial.port),
                id="conn-port",
                placeholder="6379",
                type="integer",
            )
            yield Label("Password")
            yield Input(
                value=self._initial.password or "",
                id="conn-password",
                password=True,
                placeholder="(optional)",
            )
            yield Label("Graph")
            yield Input(
                value=self._initial.graph,
                id="conn-graph",
                placeholder="graph name",
            )
            yield Select(
                [("— refresh graphs with Connect —", Select.BLANK)],
                id="conn-graph-select",
                prompt="Known graphs",
                allow_blank=True,
            )
            yield Static("", id="connection-status")
            with Horizontal(id="connection-actions"):
                yield Button("Connect", id="btn-connect", variant="primary")
                yield Button("Open", id="btn-open", variant="success")
                yield Button("Save profile", id="btn-save-profile")
                yield Button("Delete", id="btn-delete-profile")
                if self._can_dismiss:
                    yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        self._refresh_profile_select()
        default = self._profile_store.get("default")
        if default is not None:
            self._apply_profile(default)
        self.query_one("#conn-host", Input).focus()

    def action_cancel(self) -> None:
        if self._can_dismiss:
            self.dismiss(None)

    def _refresh_profile_select(self, selected: str | None = None) -> None:
        profiles = self._profile_store.list()
        select = self.query_one("#conn-profile-select", Select)
        options: list[tuple[str, str]] = [(p.name, p.name) for p in profiles]
        if not options:
            select.set_options([("— none —", Select.BLANK)])
            return
        select.set_options(options)
        if selected:
            try:
                select.value = selected
            except Exception:  # noqa: BLE001
                pass

    def _apply_profile(self, profile: Profile) -> None:
        self._applying_profile = True
        try:
            self.query_one("#conn-profile-name", Input).value = profile.name
            self.query_one("#conn-host", Input).value = profile.host
            self.query_one("#conn-port", Input).value = str(profile.port)
            self.query_one("#conn-password", Input).value = profile.password or ""
            self.query_one("#conn-graph", Input).value = profile.graph
            select = self.query_one("#conn-profile-select", Select)
            try:
                select.value = profile.name
            except Exception:  # noqa: BLE001
                pass
        finally:
            self._applying_profile = False

    def _read_fields(self) -> ConnectionConfig:
        host = self.query_one("#conn-host", Input).value.strip() or "localhost"
        port_raw = self.query_one("#conn-port", Input).value.strip() or "6379"
        password = self.query_one("#conn-password", Input).value
        graph = self.query_one("#conn-graph", Input).value.strip() or "falkorterm"
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ValueError(f"Invalid port: {port_raw}") from exc
        return replace(
            self._initial,
            host=host,
            port=port,
            password=password or None,
            graph=graph,
        )

    def _set_status(self, message: str, *, error: bool = False) -> None:
        status = self.query_one("#connection-status", Static)
        if error:
            status.update(f"[red]{message}[/]")
        else:
            status.update(f"[green]{message}[/]" if message else "")

    def _populate_graph_select(self, graphs: list[str], current: str) -> None:
        self._graphs = graphs
        select = self.query_one("#conn-graph-select", Select)
        options: list[tuple[str, str]] = [(g, g) for g in graphs]
        if current and current not in graphs:
            options = [(f"{current} (new)", current), *options]
        if not options:
            options = [(current or "falkorterm", current or "falkorterm")]
        select.set_options(options)
        try:
            select.value = current
        except Exception:  # noqa: BLE001
            pass

    @on(Select.Changed, "#conn-profile-select")
    def _on_profile_select(self, event: Select.Changed) -> None:
        if self._applying_profile or event.value is Select.BLANK:
            return
        profile = self._profile_store.get(str(event.value))
        if profile is not None:
            self._apply_profile(profile)

    @on(Select.Changed, "#conn-graph-select")
    def _on_graph_select(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return
        self.query_one("#conn-graph", Input).value = str(event.value)

    @on(Button.Pressed, "#btn-connect")
    def _on_connect(self) -> None:
        try:
            config = self._read_fields()
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        try:
            self._client.connect(config)
            graphs = self._client.list_graphs()
            self._populate_graph_select(graphs, config.graph)
            self._set_status(f"Connected · {len(graphs)} graph(s)")
        except FalkorConnectionError as exc:
            self._set_status(str(exc), error=True)

    @on(Button.Pressed, "#btn-open")
    def _on_open(self) -> None:
        try:
            config = self._read_fields()
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        config = replace(
            config,
            timeout_ms=self._initial.timeout_ms,
            max_rows=self._initial.max_rows,
        )
        try:
            same_server = (
                self._client.connected
                and self._client.config is not None
                and self._client.config.host == config.host
                and self._client.config.port == config.port
                and self._client.config.password == config.password
            )
            if same_server and self._client.config.graph != config.graph:
                self._client.select_graph(config.graph)
            elif not same_server:
                self._client.connect(config)
            else:
                # Already on the right target; refresh config timeouts.
                self._client.connect(config)
            opened = self._client.config or config
            self.dismiss(opened)
        except FalkorConnectionError as exc:
            self._set_status(str(exc), error=True)

    @on(Button.Pressed, "#btn-save-profile")
    def _on_save_profile(self) -> None:
        name = self.query_one("#conn-profile-name", Input).value.strip()
        if not name:
            self._set_status("Profile name required", error=True)
            return
        try:
            config = self._read_fields()
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return
        profile = Profile(
            name=name,
            host=config.host,
            port=config.port,
            password=config.password,
            graph=config.graph,
        )
        self._profile_store.save(profile)
        self._refresh_profile_select(selected=name)
        self._set_status(f"Saved profile “{name}”")

    @on(Button.Pressed, "#btn-delete-profile")
    def _on_delete_profile(self) -> None:
        name = self.query_one("#conn-profile-name", Input).value.strip()
        if not name:
            select = self.query_one("#conn-profile-select", Select)
            if select.value is not Select.BLANK and select.value is not None:
                name = str(select.value)
        if not name:
            self._set_status("No profile selected", error=True)
            return
        self._profile_store.delete(name)
        self.query_one("#conn-profile-name", Input).value = ""
        self._refresh_profile_select()
        self._set_status(f"Deleted profile “{name}”")

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel(self) -> None:
        self.action_cancel()
