from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from falkorterm.client.models import QueryResult

ExportFormat = Literal["csv", "json"]


def default_export_dir() -> Path:
    override = os.environ.get("FALKOR_EXPORT_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "falkorterm" / "exports"
    return Path.home() / ".local" / "share" / "falkorterm" / "exports"


def result_to_csv(result: QueryResult, *, header: bool = True) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if header and result.columns:
        writer.writerow(result.columns)
    for row in result.rows:
        writer.writerow([cell.display for cell in row])
    return buf.getvalue()


def result_to_tsv(result: QueryResult, *, header: bool = True) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
    if header and result.columns:
        writer.writerow(result.columns)
    for row in result.rows:
        writer.writerow([cell.display for cell in row])
    return buf.getvalue()


def result_to_json(result: QueryResult) -> str:
    payload = {
        "columns": list(result.columns),
        "rows": [[cell.display for cell in row] for row in result.rows],
        "truncated": result.truncated,
        "total_rows": result.total_rows,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_export(
    result: QueryResult,
    fmt: ExportFormat,
    directory: Path | None = None,
    *,
    path: Path | None = None,
    header: bool = True,
) -> Path:
    if fmt == "csv":
        content = result_to_csv(result, header=header)
    else:
        content = result_to_json(result)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
    out_dir = directory or default_export_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{stamp}.{fmt}"
    out_path.write_text(content, encoding="utf-8")
    return out_path
