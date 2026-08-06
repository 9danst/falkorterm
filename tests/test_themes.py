from falkorterm.app import FalkorTerm
from falkorterm.client.models import ConnectionConfig, GraphSchema, QueryResult
from falkorterm.themes import ALL_THEMES, DEFAULT_THEME_NAME, FLUX_1, FLUX_2, FLUX_3, LUAN, RHODIA


def test_all_themes_registered_names() -> None:
    names = {t.name for t in ALL_THEMES}
    assert names == {"falkorterm", "flux-1", "flux-2", "flux-3", "luan", "rhodia"}


def test_default_theme_is_flux_3() -> None:
    assert DEFAULT_THEME_NAME == "flux-3"
    assert FLUX_3.name == DEFAULT_THEME_NAME


def test_flux_themes_are_dark() -> None:
    for theme in (FLUX_1, FLUX_2, FLUX_3):
        assert theme.dark is True


def test_flux_3_uses_amber_warning() -> None:
    assert FLUX_3.warning == "#FFB020"


def test_flux_2_uses_cyan_secondary() -> None:
    assert FLUX_2.secondary == "#00C8E0"


def test_luan_is_dark_pure_black() -> None:
    assert LUAN.dark is True
    assert LUAN.background == "#000000"
    assert LUAN.variables is not None
    assert LUAN.variables["block-cursor-background"] == "#5CFFE7"
    assert LUAN.variables["input-cursor-background"] == "#5CFFE7"


def test_rhodia_is_dark_pure_black_with_orange_accent() -> None:
    assert RHODIA.dark is True
    assert RHODIA.background == "#000000"
    assert RHODIA.accent == "#FF6315"
    assert RHODIA.variables is not None
    assert RHODIA.variables["block-cursor-background"] == "#FF6315"
    assert RHODIA.variables["input-cursor-background"] == "#FF6315"


class _FakeClient:
    def connect(self, config: ConnectionConfig) -> None:
        pass

    def list_graphs(self) -> list[str]:
        return ["g"]

    def select_graph(self, name: str) -> None:
        pass

    def get_schema(self) -> GraphSchema:
        return GraphSchema(labels=(), relations=())

    def run_query(self, cypher: str) -> QueryResult:
        return QueryResult(columns=(), rows=(), total_rows=0, elapsed_ms=0.0)


async def test_app_mounts_with_flux_3_and_registers_all() -> None:
    app = FalkorTerm(
        config=ConnectionConfig(host="localhost", port=6379, graph="g"),
        client=_FakeClient(),  # type: ignore[arg-type]
    )
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.theme == "flux-3"
        for theme in ALL_THEMES:
            assert theme.name in app.available_themes
