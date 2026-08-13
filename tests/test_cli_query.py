import io
import json
from pathlib import Path

from falkorterm.cli import main
from falkorterm.cli_query import EXIT_NO_GRAPH, EXIT_QUERY, EXIT_USAGE, EXIT_WRITE
from falkorterm.client.models import (
    CellValue,
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
    GraphSchema,
    QueryResult,
)


def _node(nid: int, label: str = "Person") -> CellValue:
    return CellValue(
        display=f"(:{label} id={nid})",
        detail={
            "kind": "node",
            "id": nid,
            "labels": [label],
            "properties": {"name": f"n{nid}"},
        },
    )


def _edge(src: int, dest: int, rel: str = "KNOWS") -> CellValue:
    return CellValue(
        display=f"-[:{rel}]->",
        detail={
            "kind": "edge",
            "type": rel,
            "src": src,
            "dest": dest,
            "id": 9,
            "properties": {},
        },
    )


class FakeClient:
    def __init__(self) -> None:
        self.connected = False
        self.config: ConnectionConfig | None = None
        self.queries: list[str] = []
        self._graphs = ["alpha", "beta"]
        self._result = QueryResult(
            columns=("n",),
            rows=((CellValue("Ada"),),),
            total_rows=1,
            elapsed_ms=1.5,
        )
        self._schema = GraphSchema(
            labels=("Person", "Movie"),
            relations=("ACTED_IN",),
            property_keys=("name",),
            label_counts=(("Person", 2), ("Movie", 1)),
            relation_counts=(("ACTED_IN", 3),),
        )
        self.connect_error: Exception | None = None
        self.query_error: Exception | None = None

    def connect(self, config: ConnectionConfig) -> None:
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = True
        self.config = config

    def list_graphs(self) -> list[str]:
        return list(self._graphs)

    def get_schema(self) -> GraphSchema:
        return self._schema

    def run_query(self, cypher: str) -> QueryResult:
        if self.query_error is not None:
            raise self.query_error
        self.queries.append(cypher)
        return self._result


def _run(argv: list[str], client: FakeClient | None = None, stdin: str = ""):
    client = client or FakeClient()
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        argv,
        client=client,
        stdin=io.StringIO(stdin),
        stdout=stdout,
        stderr=stderr,
        run_app_fn=lambda **_: None,
    )
    return code, stdout.getvalue(), stderr.getvalue(), client


def test_query_json_stdout():
    code, out, err, client = _run(["-q", "RETURN 1", "--format", "json"])
    assert code == 0
    assert client.queries == ["RETURN 1"]
    payload = json.loads(out)
    assert payload["columns"] == ["n"]
    assert payload["rows"][0][0] == "Ada"
    assert err == ""


def test_query_from_file(tmp_path: Path):
    path = tmp_path / "q.cypher"
    path.write_text("MATCH (n) RETURN n\n", encoding="utf-8")
    code, out, _, client = _run(["-f", str(path), "--format", "csv"])
    assert code == 0
    assert client.queries == ["MATCH (n) RETURN n"]
    assert out.splitlines()[0] == "n"
    assert "Ada" in out


def test_query_from_stdin():
    code, out, _, client = _run(
        ["-q", "-", "--format", "json"],
        stdin="RETURN 1\n",
    )
    assert code == 0
    assert client.queries == ["RETURN 1"]
    assert json.loads(out)["rows"][0][0] == "Ada"


def test_query_and_file_mutually_exclusive(tmp_path: Path):
    path = tmp_path / "q.cypher"
    path.write_text("RETURN 1\n", encoding="utf-8")
    code, _, err, client = _run(["-q", "RETURN 1", "-f", str(path)])
    assert code == EXIT_USAGE
    assert "mutually exclusive" in err
    assert client.queries == []


def test_write_requires_yes():
    code, _, err, client = _run(["-q", "CREATE (n:Person)", "--format", "json"])
    assert code == EXIT_WRITE
    assert "--yes" in err
    assert client.queries == []
    assert client.connected is False


def test_write_blocked_when_read_only():
    code, _, err, client = _run(
        ["-q", "CREATE (n:Person)", "--read-only", "--yes", "--format", "json"]
    )
    assert code == EXIT_WRITE
    assert "Read-only" in err
    assert client.queries == []


def test_write_with_yes_runs():
    code, _, _, client = _run(
        ["-q", "CREATE (n:Person)", "--yes", "--format", "json"]
    )
    assert code == 0
    assert client.queries == ["CREATE (n:Person)"]


def test_connection_error_exit_2():
    client = FakeClient()
    client.connect_error = FalkorConnectionError("refused")
    code, _, err, _ = _run(["-q", "RETURN 1", "--format", "json"], client=client)
    assert code == EXIT_USAGE
    assert "refused" in err


def test_query_error_exit_1():
    client = FakeClient()
    client.query_error = FalkorQueryError("bad cypher")
    code, _, err, _ = _run(["-q", "NOT CYPHER", "--format", "json"], client=client)
    assert code == EXIT_QUERY
    assert "bad cypher" in err


def test_empty_query_is_usage():
    code, _, err, client = _run(["-q", "   "])
    assert code == EXIT_USAGE
    assert "empty" in err.lower()
    assert client.queries == []


def test_truncated_warning_on_stderr():
    client = FakeClient()
    client._result = QueryResult(
        columns=("n",),
        rows=((CellValue("Ada"),),),
        truncated=True,
        total_rows=99,
    )
    code, out, err, _ = _run(["-q", "RETURN 1", "--format", "json"], client=client)
    assert code == 0
    json.loads(out)
    assert "truncated" in err
    assert "99" in err


def test_output_file(tmp_path: Path):
    dest = tmp_path / "out.json"
    code, out, _, _ = _run(
        ["-q", "RETURN 1", "--format", "json", "--output", str(dest)]
    )
    assert code == 0
    assert out == ""
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["rows"][0][0] == "Ada"


def test_tsv_no_header():
    code, out, _, _ = _run(["-q", "RETURN 1", "--format", "tsv", "--no-header"])
    assert code == 0
    assert out == "Ada\n"


def test_diagram_ascii_file(tmp_path: Path):
    client = FakeClient()
    client._result = QueryResult(
        columns=("a", "r", "b"),
        rows=((_node(1), _edge(1, 2), _node(2)),),
        total_rows=1,
    )
    dest = tmp_path / "g.txt"
    code, out, _, _ = _run(
        [
            "-q",
            "MATCH (a)-[r]->(b) RETURN a,r,b",
            "--format",
            "json",
            "--output-diagram",
            str(dest),
        ],
        client=client,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["columns"] == ["a", "r", "b"]
    text = dest.read_text(encoding="utf-8")
    assert "id=1" in text or "Person" in text
    assert "KNOWS" in text or "-[" in text or "▶" in text or "─" in text


def test_diagram_edges_style(tmp_path: Path):
    client = FakeClient()
    client._result = QueryResult(
        columns=("a", "r", "b"),
        rows=((_node(1), _edge(1, 2), _node(2)),),
        total_rows=1,
    )
    dest = tmp_path / "edges.txt"
    code, _, _, _ = _run(
        [
            "-q",
            "MATCH (a)-[r]->(b) RETURN a,r,b",
            "--diagram-only",
            "--diagram-style",
            "edges",
            "--output-diagram",
            str(dest),
        ],
        client=client,
    )
    assert code == 0
    assert "(1)-[:KNOWS]->(2)" in dest.read_text(encoding="utf-8")


def test_diagram_stdout_conflict():
    client = FakeClient()
    client._result = QueryResult(
        columns=("a", "r", "b"),
        rows=((_node(1), _edge(1, 2), _node(2)),),
        total_rows=1,
    )
    code, _, err, _ = _run(
        [
            "-q",
            "MATCH (a)-[r]->(b) RETURN a,r,b",
            "--format",
            "json",
            "--output-diagram",
            "-",
        ],
        client=client,
    )
    assert code == EXIT_USAGE
    assert "diagram-only" in err


def test_diagram_only_stdout():
    client = FakeClient()
    client._result = QueryResult(
        columns=("a", "r", "b"),
        rows=((_node(1), _edge(1, 2), _node(2)),),
        total_rows=1,
    )
    code, out, _, _ = _run(
        [
            "-q",
            "MATCH (a)-[r]->(b) RETURN a,r,b",
            "--diagram-only",
            "--diagram-style",
            "edges",
        ],
        client=client,
    )
    assert code == 0
    assert "(1)-[:KNOWS]->(2)" in out
    assert "columns" not in out


def test_diagram_missing_graph_writes_result(tmp_path: Path):
    dest = tmp_path / "g.txt"
    code, out, err, _ = _run(
        ["-q", "RETURN 1", "--format", "json", "--output-diagram", str(dest)]
    )
    assert code == EXIT_NO_GRAPH
    assert "No graph" in err
    assert json.loads(out)["rows"][0][0] == "Ada"
    assert not dest.exists()


def test_graphs_command():
    code, out, _, client = _run(["graphs", "--format", "table"])
    assert code == 0
    assert client.connected
    assert out == "alpha\nbeta\n"


def test_graphs_json():
    code, out, _, _ = _run(["graphs", "--format", "json"])
    assert json.loads(out) == ["alpha", "beta"]


def test_schema_text_and_json():
    code, out, _, _ = _run(["schema", "--format", "table"])
    assert code == 0
    assert "Person" in out
    assert "ACTED_IN" in out
    code, out, _, _ = _run(["schema", "--format", "json"])
    payload = json.loads(out)
    assert payload["labels"] == ["Person", "Movie"]
    assert payload["label_counts"]["Person"] == 2


def test_ping_ok():
    code, out, _, client = _run(["ping"])
    assert code == 0
    assert out.startswith("ok ")
    assert client.queries == ["RETURN 1"]


def test_ping_json():
    code, out, _, _ = _run(["ping", "--format", "json"])
    payload = json.loads(out)
    assert payload["ok"] is True
    assert "target" in payload


def test_ping_connection_error():
    client = FakeClient()
    client.connect_error = FalkorConnectionError("down")
    code, _, err, _ = _run(["ping"], client=client)
    assert code == EXIT_USAGE
    assert "down" in err
