from pathlib import Path

from falkorterm.history import HistoryStore, default_history_path


def test_default_history_path_respects_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FALKOR_HISTORY_PATH", str(tmp_path / "h.json"))
    assert default_history_path() == tmp_path / "h.json"


def test_append_and_load(tmp_path: Path):
    store = HistoryStore(tmp_path / "history.json", max_entries=3)
    store.append("g@h:1", "RETURN 1")
    store.append("g@h:1", "RETURN 2")
    assert store.load("g@h:1") == ["RETURN 1", "RETURN 2"]
    assert store.load("other") == []


def test_dedupe_consecutive(tmp_path: Path):
    store = HistoryStore(tmp_path / "history.json")
    store.append("t", "RETURN 1")
    store.append("t", "RETURN 1")
    assert store.load("t") == ["RETURN 1"]


def test_trim_max_entries(tmp_path: Path):
    store = HistoryStore(tmp_path / "history.json", max_entries=2)
    store.append("t", "A")
    store.append("t", "B")
    store.append("t", "C")
    assert store.load("t") == ["B", "C"]


def test_atomic_write_creates_parent(tmp_path: Path):
    path = tmp_path / "nested" / "history.json"
    store = HistoryStore(path)
    store.append("t", "MATCH (n) RETURN n")
    assert path.exists()
    assert "MATCH (n) RETURN n" in path.read_text(encoding="utf-8")
