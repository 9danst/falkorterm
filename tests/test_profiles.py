from pathlib import Path

from falkorterm.profiles import Profile, ProfileStore, default_profiles_path


def test_default_profiles_path_respects_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FALKOR_PROFILES_PATH", str(tmp_path / "p.json"))
    assert default_profiles_path() == tmp_path / "p.json"


def test_save_get_list_delete(tmp_path: Path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(
        Profile(name="local", host="127.0.0.1", port=6380, graph="social")
    )
    store.save(Profile(name="default", host="localhost", graph="g1"))
    names = [p.name for p in store.list()]
    assert names == ["default", "local"]
    got = store.get("local")
    assert got is not None
    assert got.host == "127.0.0.1"
    assert got.port == 6380
    assert got.graph == "social"
    store.delete("local")
    assert store.get("local") is None
    assert [p.name for p in store.list()] == ["default"]


def test_save_overwrites_same_name(tmp_path: Path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(Profile(name="a", host="h1", graph="g1"))
    store.save(Profile(name="a", host="h2", graph="g2"))
    profiles = store.list()
    assert len(profiles) == 1
    assert profiles[0].host == "h2"


def test_atomic_write(tmp_path: Path):
    path = tmp_path / "nested" / "profiles.json"
    store = ProfileStore(path)
    store.save(Profile(name="x", graph="y"))
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert "x" in data
