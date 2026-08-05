import os

from falkorterm.client.models import ConnectionConfig
from falkorterm.config import load_config


def test_from_env_defaults(monkeypatch):
    for key in (
        "FALKOR_HOST",
        "FALKOR_PORT",
        "FALKOR_GRAPH",
        "FALKOR_PASSWORD",
        "FALKOR_TIMEOUT_MS",
        "FALKOR_MAX_ROWS",
        "FALKOR_READ_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = ConnectionConfig.from_env()
    assert cfg == ConnectionConfig()


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("FALKOR_HOST", "10.0.0.1")
    monkeypatch.setenv("FALKOR_PORT", "7000")
    monkeypatch.setenv("FALKOR_GRAPH", "movies")
    monkeypatch.setenv("FALKOR_PASSWORD", "secret")
    monkeypatch.setenv("FALKOR_TIMEOUT_MS", "10000")
    monkeypatch.setenv("FALKOR_MAX_ROWS", "100")
    monkeypatch.setenv("FALKOR_READ_ONLY", "true")
    cfg = ConnectionConfig.from_env()
    assert cfg.host == "10.0.0.1"
    assert cfg.port == 7000
    assert cfg.graph == "movies"
    assert cfg.password == "secret"
    assert cfg.timeout_ms == 10_000
    assert cfg.max_rows == 100
    assert cfg.read_only is True


def test_from_env_read_only_truthy(monkeypatch):
    monkeypatch.delenv("FALKOR_READ_ONLY", raising=False)
    for value in ("1", "TRUE", "Yes", "on"):
        monkeypatch.setenv("FALKOR_READ_ONLY", value)
        assert ConnectionConfig.from_env().read_only is True
    monkeypatch.setenv("FALKOR_READ_ONLY", "0")
    assert ConnectionConfig.from_env().read_only is False


def test_load_config_uses_env(monkeypatch):
    monkeypatch.setenv("FALKOR_GRAPH", "via-load")
    assert load_config().graph == "via-load"
