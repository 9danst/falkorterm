from argparse import Namespace
from pathlib import Path

import pytest

from falkorterm.cli import parse_args
from falkorterm.cli_config import ConfigError, resolve_config
from falkorterm.client.models import ConnectionConfig
from falkorterm.profiles import Profile, ProfileStore


def _clear_env(monkeypatch) -> None:
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


def test_resolve_defaults_from_env(monkeypatch):
    _clear_env(monkeypatch)
    cfg = resolve_config(parse_args([]))
    assert cfg == ConnectionConfig()


def test_flags_override_env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("FALKOR_HOST", "from-env")
    monkeypatch.setenv("FALKOR_GRAPH", "env-graph")
    monkeypatch.setenv("FALKOR_PORT", "7000")
    cfg = resolve_config(parse_args(["-H", "flag-host", "-g", "flag-graph"]))
    assert cfg.host == "flag-host"
    assert cfg.graph == "flag-graph"
    assert cfg.port == 7000


def test_profile_overrides_env_flags_override_profile(monkeypatch, tmp_path: Path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("FALKOR_HOST", "from-env")
    monkeypatch.setenv("FALKOR_GRAPH", "env-graph")
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(
        Profile(
            name="local",
            host="db.example",
            port=6381,
            graph="social",
            read_only=True,
            password="from-profile",
        )
    )
    from_profile = resolve_config(
        parse_args(["--profile", "local"]),
        profile_store=store,
    )
    assert from_profile.host == "db.example"
    assert from_profile.port == 6381
    assert from_profile.graph == "social"
    assert from_profile.read_only is True
    assert from_profile.password == "from-profile"

    from_flags = resolve_config(
        parse_args(["--profile", "local", "--host", "127.0.0.1", "-g", "other"]),
        profile_store=store,
    )
    assert from_flags.host == "127.0.0.1"
    assert from_flags.graph == "other"
    assert from_flags.port == 6381
    assert from_flags.read_only is True


def test_read_only_flag_sets_true(monkeypatch):
    _clear_env(monkeypatch)
    cfg = resolve_config(parse_args(["--read-only"]))
    assert cfg.read_only is True


def test_timeout_and_max_rows_flags(monkeypatch):
    _clear_env(monkeypatch)
    cfg = resolve_config(parse_args(["--timeout", "5000", "--max-rows", "10"]))
    assert cfg.timeout_ms == 5000
    assert cfg.max_rows == 10


def test_password_file(monkeypatch, tmp_path: Path):
    _clear_env(monkeypatch)
    path = tmp_path / "pw"
    path.write_text("s3cret\n", encoding="utf-8")
    cfg = resolve_config(parse_args(["--password-file", str(path)]))
    assert cfg.password == "s3cret"


def test_password_file_missing(monkeypatch, tmp_path: Path):
    _clear_env(monkeypatch)
    with pytest.raises(ConfigError, match="Cannot read password file"):
        resolve_config(parse_args(["--password-file", str(tmp_path / "missing")]))


def test_unknown_profile(monkeypatch, tmp_path: Path):
    _clear_env(monkeypatch)
    store = ProfileStore(tmp_path / "profiles.json")
    with pytest.raises(ConfigError, match="Unknown profile: nope"):
        resolve_config(parse_args(["--profile", "nope"]), profile_store=store)


def test_profile_keeps_env_password_when_unset(monkeypatch, tmp_path: Path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("FALKOR_PASSWORD", "env-secret")
    store = ProfileStore(tmp_path / "profiles.json")
    store.save(Profile(name="local", host="h", graph="g"))
    cfg = resolve_config(parse_args(["--profile", "local"]), profile_store=store)
    assert cfg.password == "env-secret"


def test_resolve_accepts_namespace(monkeypatch):
    _clear_env(monkeypatch)
    cfg = resolve_config(Namespace(host="x", port=1, graph="g", profile=None))
    assert cfg.host == "x"
    assert cfg.port == 1
    assert cfg.graph == "g"
