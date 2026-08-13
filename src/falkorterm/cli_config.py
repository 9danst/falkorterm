"""Resolve ConnectionConfig from CLI flags, named profiles, and the environment."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from falkorterm.client.models import ConnectionConfig
from falkorterm.profiles import ProfileStore


class ConfigError(Exception):
    """Invalid profile, password file, or connection flag."""


def resolve_config(
    args: Any,
    *,
    profile_store: ProfileStore | None = None,
) -> ConnectionConfig:
    """Merge connection settings: flags > ``--profile`` > env > defaults."""
    config = ConnectionConfig.from_env()

    profile_name = getattr(args, "profile", None)
    if profile_name:
        store = profile_store or ProfileStore()
        profile = store.get(profile_name)
        if profile is None:
            raise ConfigError(f"Unknown profile: {profile_name}")
        config = replace(
            config,
            host=profile.host,
            port=profile.port,
            graph=profile.graph,
            read_only=profile.read_only,
            password=profile.password if profile.password else config.password,
        )

    host = getattr(args, "host", None)
    if host is not None:
        config = replace(config, host=host)

    port = getattr(args, "port", None)
    if port is not None:
        config = replace(config, port=port)

    graph = getattr(args, "graph", None)
    if graph is not None:
        config = replace(config, graph=graph)

    timeout = getattr(args, "timeout", None)
    if timeout is not None:
        config = replace(config, timeout_ms=timeout)

    max_rows = getattr(args, "max_rows", None)
    if max_rows is not None:
        config = replace(config, max_rows=max_rows)

    if getattr(args, "read_only", False):
        config = replace(config, read_only=True)

    password_file = getattr(args, "password_file", None)
    if password_file:
        path = Path(password_file)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"Cannot read password file: {exc}") from exc
        password = raw.strip() or None
        config = replace(config, password=password)

    return config
