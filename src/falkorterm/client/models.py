from __future__ import annotations

import os
from dataclasses import dataclass


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ConnectionConfig:
    host: str = "localhost"
    port: int = 6379
    graph: str = "falkorterm"
    password: str | None = None
    timeout_ms: int = 30_000
    max_rows: int = 500
    read_only: bool = False

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
            read_only=_env_truthy("FALKOR_READ_ONLY"),
        )

    @property
    def display_target(self) -> str:
        return f"{self.graph}@{self.host}:{self.port}"


@dataclass(frozen=True)
class GraphSchema:
    labels: tuple[str, ...]
    relations: tuple[str, ...]
    property_keys: tuple[str, ...] = ()
    label_counts: tuple[tuple[str, int], ...] = ()
    relation_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class CellValue:
    display: str
    detail: dict[str, object] | None = None

    def __str__(self) -> str:
        return self.display


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[CellValue, ...], ...]
    truncated: bool = False
    total_rows: int = 0
    elapsed_ms: float | None = None


class FalkorConnectionError(Exception):
    """Raised when connecting to FalkorDB fails."""


class FalkorQueryError(Exception):
    """Raised when a Cypher query fails."""
