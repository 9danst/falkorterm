from textual.app import App, ComposeResult
from textual.widgets import Input, Static

from falkorterm.client.models import ConnectionConfig
from falkorterm.profiles import Profile, ProfileStore
from falkorterm.screens.connection import ConnectionScreen


class FakeClient:
    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self._graphs = ["alpha", "beta"]

    def connect(self, config: ConnectionConfig) -> None:
        self.connected = True
        self.config = config

    def list_graphs(self) -> list[str]:
        return list(self._graphs)

    def select_graph(self, name: str) -> None:
        assert self.config is not None
        from dataclasses import replace

        self.config = replace(self.config, graph=name)


class ConnectionHarness(App):
    def __init__(self, profile_store: ProfileStore | None = None) -> None:
        super().__init__()
        self.client = FakeClient()
        self.result: ConnectionConfig | None = None
        self.profile_store = profile_store or ProfileStore()

    def compose(self) -> ComposeResult:
        yield Static("background")

    def on_mount(self) -> None:
        self.push_screen(
            ConnectionScreen(
                ConnectionConfig(host="localhost", port=6379, graph="alpha"),
                self.client,  # type: ignore[arg-type]
                can_dismiss=True,
                profile_store=self.profile_store,
            ),
            self._capture,
        )

    def _capture(self, result: ConnectionConfig | None) -> None:
        self.result = result


async def test_connection_screen_open_dismisses_config(tmp_path):
    app = ConnectionHarness(profile_store=ProfileStore(tmp_path / "p.json"))
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen._on_open()
        await pilot.pause()
        assert app.result is not None
        assert app.result.graph == "alpha"
        assert app.result.host == "localhost"
        assert app.result.read_only is False
        assert app.client.connected


async def test_connection_screen_connect_lists_graphs(tmp_path):
    app = ConnectionHarness(profile_store=ProfileStore(tmp_path / "p.json"))
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen._on_connect()
        await pilot.pause()
        assert app.client.connected
        status = screen.query_one("#connection-status")
        assert "2 graph" in str(status.render())


async def test_connection_screen_applies_saved_profile(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(
        Profile(
            name="staging",
            host="db.example",
            port=6381,
            password="secret",
            graph="prod",
            read_only=True,
        )
    )
    app = ConnectionHarness(profile_store=store)
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen._apply_profile(store.get("staging"))  # type: ignore[arg-type]
        await pilot.pause()
        assert screen.query_one("#conn-host", Input).value == "db.example"
        assert screen.query_one("#conn-port", Input).value == "6381"
        assert screen.query_one("#conn-password", Input).value == "secret"
        assert screen.query_one("#conn-graph", Input).value == "prod"
        assert screen.query_one("#conn-profile-name", Input).value == "staging"
        assert screen.query_one("#conn-read-only").value is True


async def test_connection_screen_save_profile(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    app = ConnectionHarness(profile_store=store)
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen.query_one("#conn-profile-name", Input).value = "mine"
        screen.query_one("#conn-host", Input).value = "h"
        screen.query_one("#conn-graph", Input).value = "g"
        screen.query_one("#conn-read-only").value = True
        screen._on_save_profile()
        await pilot.pause()
        saved = store.get("mine")
        assert saved is not None
        assert saved.host == "h"
        assert saved.graph == "g"
        assert saved.read_only is True


async def test_connection_screen_open_preserves_read_only(tmp_path):
    app = ConnectionHarness(profile_store=ProfileStore(tmp_path / "p.json"))
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ConnectionScreen)
        screen.query_one("#conn-read-only").value = True
        screen._on_open()
        await pilot.pause()
        assert app.result is not None
        assert app.result.read_only is True
