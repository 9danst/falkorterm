from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

from falkordb import FalkorDB

from falkorterm.client.cells import to_cell_value
from falkorterm.client.models import (
    CellValue,
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
    GraphSchema,
    QueryResult,
)


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

    def abort_and_reconnect(self) -> None:
        """Close the live connection to unblock an in-flight query, then reconnect."""
        cfg = self._config
        try:
            if self._db is not None:
                self._db.close()
        except Exception:  # noqa: BLE001 — best-effort close
            pass
        finally:
            self._db = None
            self._graph = None
        if cfg is not None:
            self.connect(cfg)

    def list_graphs(self) -> list[str]:
        if self._db is None:
            raise FalkorConnectionError("Not connected to FalkorDB")
        try:
            graphs = self._db.list_graphs()
            return [str(g) for g in (graphs or [])]
        except FalkorConnectionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FalkorConnectionError(str(exc)) from exc

    def select_graph(self, name: str) -> None:
        if self._db is None:
            raise FalkorConnectionError("Not connected to FalkorDB")
        try:
            self._graph = self._db.select_graph(name)
            if self._config is None:
                self._config = ConnectionConfig(graph=name)
            else:
                self._config = replace(self._config, graph=name)
        except FalkorConnectionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FalkorConnectionError(str(exc)) from exc

    def get_schema(self) -> GraphSchema:
        graph = self._require_graph()
        try:
            labels = self._procedure_names(graph, "CALL db.labels()")
            relations = self._procedure_names(
                graph, "CALL db.relationshipTypes()"
            )
            try:
                property_keys = self._procedure_names(
                    graph, "CALL db.propertyKeys()"
                )
            except FalkorQueryError:
                property_keys = []

            label_counts = self._safe_counts(
                graph,
                "MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS c",
                labels,
            )
            relation_counts = self._safe_counts(
                graph,
                "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c",
                relations,
            )
            return GraphSchema(
                labels=tuple(labels),
                relations=tuple(relations),
                property_keys=tuple(property_keys),
                label_counts=tuple(label_counts),
                relation_counts=tuple(relation_counts),
            )
        except FalkorQueryError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise FalkorQueryError(str(exc)) from exc

    def run_query(self, cypher: str) -> QueryResult:
        graph = self._require_graph()
        assert self._config is not None
        started = time.perf_counter()
        try:
            raw = graph.query(cypher, timeout=self._config.timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise FalkorQueryError(str(exc)) from exc
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        columns = tuple(_header_name(h) for h in (getattr(raw, "header", None) or []))
        result_set = list(getattr(raw, "result_set", None) or [])
        total_rows = len(result_set)
        max_rows = self._config.max_rows
        truncated = total_rows > max_rows
        if truncated:
            result_set = result_set[:max_rows]

        rows: list[tuple[CellValue, ...]] = []
        for row in result_set:
            cells = tuple(to_cell_value(cell) for cell in row)
            rows.append(cells)

        if not columns and rows:
            columns = tuple(f"col_{i}" for i in range(len(rows[0])))

        return QueryResult(
            columns=columns,
            rows=tuple(rows),
            truncated=truncated,
            total_rows=total_rows,
            elapsed_ms=elapsed_ms,
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

    @staticmethod
    def _safe_counts(
        graph: Any, cypher: str, names: list[str]
    ) -> list[tuple[str, int]]:
        """Return counts aligned to `names`; degrade to zeros on failure."""
        ordered = list(names)
        counts: dict[str, int] = {name: 0 for name in ordered}
        try:
            raw = graph.query(cypher)
        except Exception:  # noqa: BLE001
            return [(name, 0) for name in ordered]
        for row in getattr(raw, "result_set", None) or []:
            if not row or len(row) < 2:
                continue
            key = str(row[0])
            try:
                value = int(row[1])
            except (TypeError, ValueError):
                value = 0
            counts[key] = value
            if key not in counts or key not in ordered:
                if key not in ordered:
                    ordered.append(key)
        return [(name, counts.get(name, 0)) for name in ordered]
