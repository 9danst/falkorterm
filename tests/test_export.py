import csv
import json
from pathlib import Path

from falkorterm.client.models import CellValue, QueryResult
from falkorterm.export import (
    default_export_dir,
    result_to_csv,
    result_to_json,
    result_to_tsv,
    write_export,
)


def _sample_result() -> QueryResult:
    return QueryResult(
        columns=("name", "note"),
        rows=(
            (CellValue('Ada "Lovelace"'), CellValue("line1\nline2")),
            (CellValue("Bob"), CellValue("ok")),
        ),
        total_rows=2,
        truncated=False,
    )


def test_result_to_csv_escapes_quotes_and_newlines():
    import io

    text = result_to_csv(_sample_result())
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["name", "note"]
    assert rows[1][0] == 'Ada "Lovelace"'
    assert rows[1][1] == "line1\nline2"


def test_result_to_json_structure():
    payload = json.loads(result_to_json(_sample_result()))
    assert payload["columns"] == ["name", "note"]
    assert payload["rows"][0][0] == 'Ada "Lovelace"'
    assert payload["total_rows"] == 2
    assert payload["truncated"] is False


def test_default_export_dir_respects_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("FALKOR_EXPORT_DIR", str(tmp_path / "out"))
    assert default_export_dir() == tmp_path / "out"


def test_write_export_creates_file(tmp_path: Path):
    path = write_export(_sample_result(), "csv", directory=tmp_path)
    assert path.parent == tmp_path
    assert path.suffix == ".csv"
    assert path.exists()
    assert "name,note" in path.read_text(encoding="utf-8")

    path_json = write_export(_sample_result(), "json", directory=tmp_path)
    assert path_json.suffix == ".json"
    data = json.loads(path_json.read_text(encoding="utf-8"))
    assert data["columns"] == ["name", "note"]


def test_result_to_csv_no_header():
    text = result_to_csv(_sample_result(), header=False)
    assert not text.startswith("name")
    assert "Ada" in text


def test_result_to_tsv():
    text = result_to_tsv(_sample_result())
    assert text.splitlines()[0] == "name\tnote"
    assert "Ada" in text


def test_write_export_explicit_path(tmp_path: Path):
    dest = tmp_path / "nested" / "out.json"
    path = write_export(_sample_result(), "json", path=dest)
    assert path == dest
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["columns"] == ["name", "note"]
