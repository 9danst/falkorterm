from __future__ import annotations

from typing import Any

from falkordb import FalkorDB

from falkorterm.client.models import (
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
    GraphSchema,
    QueryResult,
)


def _cell_to_display(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _header_name(entry: Any) -> str:
    """FalkorDB headers are often [column_type, column_name] pairs."""
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        return str(entry[-1])
    return str(entry)


class FalkorClient:
    """Thin wrapper around the official falkordb SDK."""

    def __init__(self) -> None:
        self._db: FalkorDB | None = None
        self._graph: Any = None
        self._config: ConnectionConfig | None = None

    @property
    def config(self) -> ConnectionConfig | None:
        return self._config

    @property
    def connected(self) -> bool:
        return self._graph is not None

    def connect(self, config: ConnectionConfig) -> None:
        try:
            kwargs: dict[str, Any] = {
                "host": config.host,
                "port": config.port,
            }
            if config.password is not None:
                kwargs["password"] = config.password
            db = FalkorDB(**kwargs)
            # Touch the connection early so failures surface here.
            db.list_graphs()
            self._db = db
            self._graph = db.select_graph(config.graph)
            self._config = config
        except FalkorConnectionError:
            raise
        except Exception as exc:  # noqa: BLE001 — map SDK/redis errors
            self._db = None
            self._graph = None
            self._config = None
            raise FalkorConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        self._db = None
        self._graph = None
        self._config = None

    def get_schema(self) -> GraphSchema:
        graph = self._require_graph()
        try:
            labels = self._procedure_names(graph, "CALL db.labels()")
            relations = self._procedure_names(graph, "CALL db.relationshipTypes()")
            return GraphSchema(labels=tuple(labels), relations=tuple(relations))
        except FalkorQueryError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FalkorQueryError(str(exc)) from exc

    def run_query(self, cypher: str) -> QueryResult:
        graph = self._require_graph()
        assert self._config is not None
        try:
            raw = graph.query(cypher, timeout=self._config.timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise FalkorQueryError(str(exc)) from exc

        columns = tuple(_header_name(h) for h in (getattr(raw, "header", None) or []))
        result_set = list(getattr(raw, "result_set", None) or [])
        total_rows = len(result_set)
        max_rows = self._config.max_rows
        truncated = total_rows > max_rows
        if truncated:
            result_set = result_set[:max_rows]

        rows: list[tuple[object, ...]] = []
        for row in result_set:
            cells = tuple(_cell_to_display(cell) for cell in row)
            rows.append(cells)

        if not columns and rows:
            columns = tuple(f"col_{i}" for i in range(len(rows[0])))

        return QueryResult(
            columns=columns,
            rows=tuple(rows),
            truncated=truncated,
            total_rows=total_rows,
        )

    def _require_graph(self) -> Any:
        if self._graph is None:
            raise FalkorConnectionError("Not connected to FalkorDB")
        return self._graph

    @staticmethod
    def _procedure_names(graph: Any, cypher: str) -> list[str]:
        try:
            raw = graph.query(cypher)
        except Exception as exc:  # noqa: BLE001
            raise FalkorQueryError(str(exc)) from exc
        names: list[str] = []
        for row in getattr(raw, "result_set", None) or []:
            if not row:
                continue
            value = row[0]
            names.append(str(value))
        return names
