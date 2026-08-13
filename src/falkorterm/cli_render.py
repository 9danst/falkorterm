"""Headless formatters for query results, schema, and ASCII diagrams."""

from __future__ import annotations

import io
import json
import os

from rich.console import Console
from rich.table import Table

from falkorterm.client.models import GraphSchema, QueryResult
from falkorterm.export import result_to_csv, result_to_json, result_to_tsv
from falkorterm.graph.extract import extract_graph
from falkorterm.graph.layout import layout_ascii
from falkorterm.graph.layout_coords import format_session_text
from falkorterm.graph.models import GraphViewModel

CLI_FORMATS = ("table", "csv", "tsv", "json")
DIAGRAM_STYLES = ("ascii", "edges")


def stream_isatty(stream: object) -> bool:
    check = getattr(stream, "isatty", None)
    if check is None:
        return False
    try:
        return bool(check())
    except Exception:  # noqa: BLE001 — pipes / StringIO
        return False


def default_format(*, stdout_isatty: bool) -> str:
    return "table" if stdout_isatty else "json"


def want_color(*, no_color: bool, stdout_isatty: bool) -> bool:
    if no_color:
        return False
    if os.environ.get("NO_COLOR", "").strip():
        return False
    return stdout_isatty


def result_to_table(result: QueryResult, *, color: bool = False) -> str:
    if not result.columns and not result.rows:
        return "(no rows)\n"
    buf = io.StringIO()
    console = Console(
        file=buf,
        force_terminal=color,
        color_system="standard" if color else None,
        highlight=False,
        width=120,
        legacy_windows=False,
    )
    table = Table(show_header=bool(result.columns))
    for column in result.columns:
        table.add_column(column)
    if not result.columns and result.rows:
        width = len(result.rows[0])
        for index in range(width):
            table.add_column(f"col_{index}")
    for row in result.rows:
        table.add_row(*[cell.display for cell in row])
    console.print(table)
    text = buf.getvalue()
    if not text.endswith("\n"):
        text += "\n"
    return text


def format_result(
    result: QueryResult,
    fmt: str,
    *,
    header: bool = True,
    color: bool = False,
) -> str:
    if fmt == "json":
        return result_to_json(result)
    if fmt == "csv":
        return result_to_csv(result, header=header)
    if fmt == "tsv":
        return result_to_tsv(result, header=header)
    if fmt == "table":
        return result_to_table(result, color=color)
    raise ValueError(f"Unsupported format: {fmt}")


def render_diagram(
    result: QueryResult,
    *,
    style: str = "ascii",
    max_nodes: int = 25,
    max_edges: int = 40,
) -> tuple[str, GraphViewModel]:
    model = extract_graph(result, max_nodes=max_nodes, max_edges=max_edges)
    if style == "edges":
        return format_session_text(model), model
    canvas = layout_ascii(model, selected_id=None, include_header=True)
    return canvas.text, model


def format_schema(schema: GraphSchema, fmt: str) -> str:
    if fmt == "json":
        payload = {
            "labels": list(schema.labels),
            "relations": list(schema.relations),
            "property_keys": list(schema.property_keys),
            "label_counts": dict(schema.label_counts),
            "relation_counts": dict(schema.relation_counts),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    label_counts = dict(schema.label_counts)
    relation_counts = dict(schema.relation_counts)
    lines: list[str] = []
    lines.append(f"Labels ({len(schema.labels)}):")
    if schema.labels:
        for name in schema.labels:
            if name in label_counts:
                lines.append(f"  {name}  {label_counts[name]}")
            else:
                lines.append(f"  {name}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(f"Relationships ({len(schema.relations)}):")
    if schema.relations:
        for name in schema.relations:
            if name in relation_counts:
                lines.append(f"  {name}  {relation_counts[name]}")
            else:
                lines.append(f"  {name}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Property keys:")
    if schema.property_keys:
        for key in schema.property_keys:
            lines.append(f"  {key}")
    else:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def format_graphs(graphs: list[str], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(graphs, indent=2, ensure_ascii=False) + "\n"
    if not graphs:
        return ""
    return "\n".join(graphs) + "\n"
