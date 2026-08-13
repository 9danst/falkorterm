"""Command-line entry for FalkorTerm (TUI and headless)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from falkorterm import __version__
from falkorterm.app import run_app
from falkorterm.cli_config import ConfigError, resolve_config
from falkorterm.cli_query import (
    EXIT_USAGE,
    run_graphs,
    run_headless_query,
    run_ping,
    run_schema,
)
from falkorterm.cli_render import CLI_FORMATS, DIAGRAM_STYLES
from falkorterm.client.models import ConnectionConfig
from falkorterm.profiles import ProfileStore

_EPILOG = """\
examples:
  falkorterm
  falkorterm --profile local --skip-connect
  falkorterm -q 'MATCH (n) RETURN n LIMIT 10'
  falkorterm -q 'MATCH (a)-[r]->(b) RETURN a,r,b' --output-diagram graph.txt
  echo 'RETURN 1' | falkorterm -q - --format json
  falkorterm graphs
  falkorterm schema --format json
  falkorterm ping
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="falkorterm",
        description="TUI and CLI client for FalkorDB.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("tui", "graphs", "schema", "ping"),
        help="tui (default), or a headless inspect command",
    )

    conn = parser.add_argument_group("connection")
    conn.add_argument("-H", "--host", help="FalkorDB host (default: env/localhost)")
    conn.add_argument("-P", "--port", type=int, help="FalkorDB port (default: 6379)")
    conn.add_argument("-g", "--graph", help="graph name (default: env/falkorterm)")
    conn.add_argument(
        "--password-file",
        metavar="PATH",
        help="read password from file (avoids exposing it in ps)",
    )
    conn.add_argument("--profile", help="named connection profile")
    conn.add_argument(
        "-r",
        "--read-only",
        action="store_true",
        help="block write queries in the client",
    )
    conn.add_argument(
        "--timeout",
        type=int,
        metavar="MS",
        help="query timeout in milliseconds",
    )
    conn.add_argument(
        "--max-rows",
        type=int,
        dest="max_rows",
        help="max rows returned to the client",
    )
    conn.add_argument(
        "--skip-connect",
        action="store_true",
        help="TUI: connect with resolved settings and skip the connection screen",
    )

    query = parser.add_argument_group("query")
    query.add_argument(
        "-q",
        "--query",
        metavar="CYPHER",
        help="Cypher to run headless; use - to read stdin",
    )
    query.add_argument(
        "-f",
        "--query-file",
        metavar="PATH",
        dest="query_file",
        help="read Cypher from a file",
    )
    query.add_argument(
        "-o",
        "--format",
        choices=CLI_FORMATS,
        help="output format (default: table on TTY, json otherwise)",
    )
    query.add_argument(
        "--output",
        metavar="PATH",
        help="write query results to a file instead of stdout",
    )
    query.add_argument(
        "--no-header",
        action="store_true",
        help="omit column header in csv/tsv output",
    )
    query.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="confirm write queries in headless mode",
    )
    query.add_argument(
        "--no-color",
        action="store_true",
        help="disable color in table output",
    )
    query.add_argument(
        "--output-diagram",
        metavar="PATH",
        dest="output_diagram",
        help="write an ASCII graph diagram to PATH (- for stdout)",
    )
    query.add_argument(
        "--diagram-style",
        choices=DIAGRAM_STYLES,
        default="ascii",
        dest="diagram_style",
        help="ascii boxes (default) or edge list",
    )
    query.add_argument(
        "--diagram-only",
        action="store_true",
        dest="diagram_only",
        help="do not print the tabular result",
    )
    query.add_argument(
        "--max-nodes",
        type=int,
        default=25,
        dest="max_nodes",
        help="max nodes in the diagram (default: 25)",
    )
    query.add_argument(
        "--max-edges",
        type=int,
        default=40,
        dest="max_edges",
        help="max edges in the diagram (default: 40)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _has_query(args: argparse.Namespace) -> bool:
    return args.query is not None or args.query_file is not None


def _has_output_flags(args: argparse.Namespace) -> bool:
    return bool(
        args.output
        or args.output_diagram
        or args.diagram_only
        or args.no_header
        or args.format
    )


def dispatch(
    args: argparse.Namespace,
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    client: Any | None,
    profile_store: ProfileStore | None,
    run_app_fn: Callable[..., None],
) -> int:
    try:
        config = resolve_config(args, profile_store=profile_store)
    except ConfigError as exc:
        print(exc, file=stderr)
        return EXIT_USAGE

    command = args.command
    has_query = _has_query(args)

    if has_query and command is not None:
        print("query options cannot be combined with a subcommand", file=stderr)
        return EXIT_USAGE

    if command in {"graphs", "schema", "ping"}:
        if command == "graphs":
            return run_graphs(
                args, config, client=client, stdout=stdout, stderr=stderr
            )
        if command == "schema":
            return run_schema(
                args, config, client=client, stdout=stdout, stderr=stderr
            )
        return run_ping(args, config, client=client, stdout=stdout, stderr=stderr)

    if has_query:
        return run_headless_query(
            args,
            config,
            client=client,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

    if _has_output_flags(args):
        print("output options require --query or --query-file", file=stderr)
        return EXIT_USAGE

    run_app_fn(config, skip_connect=args.skip_connect)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    client: Any | None = None,
    profile_store: ProfileStore | None = None,
    run_app_fn: Callable[..., None] | None = None,
) -> int:
    args = parse_args(argv)
    return dispatch(
        args,
        stdin=stdin or sys.stdin,
        stdout=stdout or sys.stdout,
        stderr=stderr or sys.stderr,
        client=client,
        profile_store=profile_store,
        run_app_fn=run_app_fn or _run_app,
    )


def _run_app(config: ConnectionConfig, *, skip_connect: bool = False) -> None:
    run_app(config, skip_connect=skip_connect)
