"""Load connection settings from the environment."""

from falkorterm.client.models import ConnectionConfig


def load_config() -> ConnectionConfig:
    return ConnectionConfig.from_env()
