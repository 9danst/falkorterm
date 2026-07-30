from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionConfig:
    host: str = "localhost"
    port: int = 6379
    graph: str = "falkorterm"
    password: str | None = None
    timeout_ms: int = 30_000
    max_rows: int = 500

    @classmethod
    def from_env(cls) -> ConnectionConfig:
        password = os.environ.get("FALKOR_PASSWORD") or None
        return cls(
            host=os.environ.get("FALKOR_HOST", "localhost"),
            port=int(os.environ.get("FALKOR_PORT", "6379")),
            graph=os.environ.get("FALKOR_GRAPH", "falkorterm"),
            password=password,
            timeout_ms=int(os.environ.get("FALKOR_TIMEOUT_MS", "30000")),
            max_rows=int(os.environ.get("FALKOR_MAX_ROWS", "500")),
        )

    @property
    def display_target(self) -> str:
        return f"{self.graph}@{self.host}:{self.port}"


@dataclass(frozen=True)
class GraphSchema:
    labels: tuple[str, ...]
    relations: tuple[str, ...]


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    truncated: bool = False
    total_rows: int = 0


class FalkorConnectionError(Exception):
    """Raised when connecting to FalkorDB fails."""


class FalkorQueryError(Exception):
    """Raised when a Cypher query fails."""
