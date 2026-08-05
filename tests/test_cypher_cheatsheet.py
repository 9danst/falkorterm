from textual.app import App, ComposeResult

from falkorterm.cheatsheet import load_cheatsheet
from falkorterm.screens.cypher_cheatsheet import CypherCheatsheetScreen
from falkorterm.widgets.query import QueryWidget


class QueryHarness(App):
    def compose(self) -> ComposeResult:
        yield QueryWidget(id="query")


async def _open_cheatsheet_with_key(key: str) -> None:
    app = QueryHarness()
    async with app.run_test(size=(100, 40)) as pilot:
        app.query_one("#query", QueryWidget).query_one("#cypher-input").focus()
        await pilot.pause()
        await pilot.press(key)
        await pilot.pause()
        assert isinstance(app.screen, CypherCheatsheetScreen)


async def test_f4_opens_cheatsheet_from_query():
    await _open_cheatsheet_with_key("f4")


async def test_ctrl_shift_h_opens_cheatsheet_from_query():
    await _open_cheatsheet_with_key("ctrl+shift+h")


async def test_ctrl_h_opens_cheatsheet_from_query():
    await _open_cheatsheet_with_key("ctrl+h")


async def test_cheatsheet_escape_closes():
    class Harness(App):
        def on_mount(self) -> None:
            self.push_screen(CypherCheatsheetScreen())

    app = Harness()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, CypherCheatsheetScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, CypherCheatsheetScreen)


def test_cheatsheet_content_has_core_sections():
    text = load_cheatsheet()
    assert "MATCH" in text
    assert "MERGE" in text
    assert "db.labels" in text
    assert "Limitations" in text or "limitations" in text
