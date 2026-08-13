"""Headless Cypher execution, write-guard, and inspect commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TextIO

import json

from falkorterm.cli_render import (
    default_format,
    format_graphs,
    format_result,
    format_schema,
    render_diagram,
    stream_isatty,
    want_color,
)
from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import (
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
)
from falkorterm.write_guard import is_write_query

EXIT_OK = 0
EXIT_QUERY = 1
EXIT_USAGE = 2
EXIT_WRITE = 3
EXIT_NO_GRAPH = 4


class QueryCliError(Exception):
    def __init__(self, message: str, code: int = EXIT_USAGE) -> None:
        super().__init__(message)
        self.code = code


def read_cypher(
    args: Any,
    *,
    stdin: TextIO,
) -> str:
    query = getattr(args, "query", None)
    query_file = getattr(args, "query_file", None)
    if query is not None and query_file is not None:
        raise QueryCliError("--query and --query-file are mutually exclusive")
    if query_file is not None:
        path = Path(query_file)
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise QueryCliError(f"Cannot read query file: {exc}") from exc
    if query is None:
        raise QueryCliError("No query provided (use -q, -f, or -q -)")
    if query == "-":
        return stdin.read()
    return query


def _resolved_format(args: Any, stdout: TextIO) -> str:
    fmt = getattr(args, "format", None)
    if fmt:
        return fmt
    return default_format(stdout_isatty=stream_isatty(stdout))


def _write_text(text: str, destination: str | None, stdout: TextIO) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if destination is None or destination == "-":
        stdout.write(text)
        return
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _connect(client: Any, config: ConnectionConfig) -> None:
    try:
        client.connect(config)
    except FalkorConnectionError as exc:
        raise QueryCliError(str(exc), EXIT_USAGE) from exc


def run_headless_query(
    args: Any,
    config: ConnectionConfig,
    *,
    client: Any | None = None,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        cypher = read_cypher(args, stdin=stdin).strip()
    except QueryCliError as exc:
        print(exc, file=stderr)
        return exc.code
    if not cypher:
        print("Query is empty", file=stderr)
        return EXIT_USAGE

    if is_write_query(cypher):
        if config.read_only:
            print("Read-only connection: write queries are blocked.", file=stderr)
            return EXIT_WRITE
        if not getattr(args, "yes", False):
            print("Write query requires --yes", file=stderr)
            return EXIT_WRITE

    diagram_path = getattr(args, "output_diagram", None)
    diagram_only = getattr(args, "diagram_only", False)
    output_path = getattr(args, "output", None)
    fmt = _resolved_format(args, stdout)

    result_to_stdout = not diagram_only and (output_path is None or output_path == "-")
    diagram_to_stdout = diagram_path == "-"
    if result_to_stdout and diagram_to_stdout:
        print(
            "--output-diagram - conflicts with result stdout; use --diagram-only",
            file=stderr,
        )
        return EXIT_USAGE
    if diagram_only and diagram_path is None:
        diagram_path = "-"
        diagram_to_stdout = True

    db = client or FalkorClient()
    try:
        _connect(db, config)
    except QueryCliError as exc:
        print(exc, file=stderr)
        return exc.code

    try:
        result = db.run_query(cypher)
    except FalkorQueryError as exc:
        print(exc, file=stderr)
        return EXIT_QUERY
    except FalkorConnectionError as exc:
        print(exc, file=stderr)
        return EXIT_USAGE

    if result.truncated:
        print(
            f"truncated: showing {len(result.rows)} of {result.total_rows} rows",
            file=stderr,
        )

    exit_code = EXIT_OK
    if diagram_path is not None or diagram_only:
        text, model = render_diagram(
            result,
            style=getattr(args, "diagram_style", None) or "ascii",
            max_nodes=getattr(args, "max_nodes", 25),
            max_edges=getattr(args, "max_edges", 40),
        )
        if not model.nodes:
            print("No graph in query result to diagram", file=stderr)
            exit_code = EXIT_NO_GRAPH
        else:
            if model.truncated:
                print(
                    "diagram truncated: "
                    f"{model.total_nodes} nodes, {model.total_edges} edges",
                    file=stderr,
                )
            _write_text(text, diagram_path, stdout)

    if not diagram_only:
        color = want_color(
            no_color=getattr(args, "no_color", False),
            stdout_isatty=stream_isatty(stdout) and result_to_stdout,
        )
        payload = format_result(
            result,
            fmt,
            header=not getattr(args, "no_header", False),
            color=color,
        )
        _write_text(payload, output_path, stdout)

    return exit_code


def run_graphs(
    args: Any,
    config: ConnectionConfig,
    *,
    client: Any | None = None,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    db = client or FalkorClient()
    try:
        _connect(db, config)
        graphs = db.list_graphs()
    except QueryCliError as exc:
        print(exc, file=stderr)
        return exc.code
    except FalkorConnectionError as exc:
        print(exc, file=stderr)
        return EXIT_USAGE
    fmt = _resolved_format(args, stdout)
    if fmt == "table":
        fmt = "text"
    stdout.write(format_graphs(graphs, "json" if fmt == "json" else "text"))
    return EXIT_OK


def run_schema(
    args: Any,
    config: ConnectionConfig,
    *,
    client: Any | None = None,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    db = client or FalkorClient()
    try:
        _connect(db, config)
        schema = db.get_schema()
    except QueryCliError as exc:
        print(exc, file=stderr)
        return exc.code
    except FalkorConnectionError as exc:
        print(exc, file=stderr)
        return EXIT_USAGE
    except FalkorQueryError as exc:
        print(exc, file=stderr)
        return EXIT_QUERY
    fmt = _resolved_format(args, stdout)
    stdout.write(format_schema(schema, "json" if fmt == "json" else "text"))
    return EXIT_OK


def run_ping(
    args: Any,
    config: ConnectionConfig,
    *,
    client: Any | None = None,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    db = client or FalkorClient()
    try:
        _connect(db, config)
        db.run_query("RETURN 1")
    except QueryCliError as exc:
        print(exc, file=stderr)
        return exc.code
    except FalkorConnectionError as exc:
        print(exc, file=stderr)
        return EXIT_USAGE
    except FalkorQueryError as exc:
        print(exc, file=stderr)
        return EXIT_QUERY
    fmt = getattr(args, "format", None)
    if fmt == "json":
        payload = {"ok": True, "target": config.display_target}
        stdout.write(json.dumps(payload) + "\n")
    else:
        stdout.write(f"ok {config.display_target}\n")
    return EXIT_OK
