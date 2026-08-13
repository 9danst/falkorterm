import json

from falkorterm.cli_render import (
    default_format,
    format_graphs,
    format_result,
    format_schema,
    render_diagram,
    result_to_table,
    result_to_tsv,
    want_color,
)
from falkorterm.client.models import CellValue, GraphSchema, QueryResult


def _sample() -> QueryResult:
    return QueryResult(
        columns=("name", "note"),
        rows=(
            (CellValue("Ada"), CellValue("ok")),
            (CellValue("Bob"), CellValue("x\ty")),
        ),
        total_rows=2,
    )


def _graph_result() -> QueryResult:
    def node(nid: int) -> CellValue:
        return CellValue(
            display=f"(:Person id={nid})",
            detail={
                "kind": "node",
                "id": nid,
                "labels": ["Person"],
                "properties": {"name": f"n{nid}"},
            },
        )
    edge = CellValue(
        display="-[:KNOWS]->",
        detail={
            "kind": "edge",
            "type": "KNOWS",
            "src": 1,
            "dest": 2,
            "id": 9,
            "properties": {},
        },
    )
    return QueryResult(
        columns=("a", "r", "b"),
        rows=((node(1), edge, node(2)),),
        total_rows=1,
    )


def test_default_format_tty_vs_pipe():
    assert default_format(stdout_isatty=True) == "table"
    assert default_format(stdout_isatty=False) == "json"


def test_want_color_respects_no_color_and_env(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert want_color(no_color=False, stdout_isatty=True) is True
    assert want_color(no_color=True, stdout_isatty=True) is False
    assert want_color(no_color=False, stdout_isatty=False) is False
    monkeypatch.setenv("NO_COLOR", "1")
    assert want_color(no_color=False, stdout_isatty=True) is False


def test_result_to_tsv_escapes_tabs():
    text = result_to_tsv(_sample())
    lines = text.splitlines()
    assert lines[0] == "name\tnote"
    assert lines[1] == "Ada\tok"
    assert "Bob" in lines[2]


def test_result_to_tsv_no_header():
    text = result_to_tsv(_sample(), header=False)
    assert not text.startswith("name")
    assert text.startswith("Ada")


def test_format_result_json_and_csv():
    json_text = format_result(_sample(), "json")
    payload = json.loads(json_text)
    assert payload["columns"] == ["name", "note"]
    csv_text = format_result(_sample(), "csv")
    assert csv_text.splitlines()[0] == "name,note"


def test_result_to_table_includes_values():
    text = result_to_table(_sample(), color=False)
    assert "Ada" in text
    assert "Bob" in text
    assert "name" in text


def test_render_diagram_ascii_and_edges():
    ascii_text, model = render_diagram(_graph_result(), style="ascii")
    assert model.nodes
    assert "Person" in ascii_text or "id=1" in ascii_text
    edges_text, _ = render_diagram(_graph_result(), style="edges")
    assert "(1)-[:KNOWS]->(2)" in edges_text


def test_render_diagram_empty_result():
    text, model = render_diagram(
        QueryResult(columns=("n",), rows=((CellValue("x"),),), total_rows=1),
        style="edges",
    )
    assert not model.nodes
    assert text


def test_format_schema_json_and_text():
    schema = GraphSchema(
        labels=("Person",),
        relations=("KNOWS",),
        property_keys=("name",),
        label_counts=(("Person", 4),),
        relation_counts=(("KNOWS", 2),),
    )
    payload = json.loads(format_schema(schema, "json"))
    assert payload["labels"] == ["Person"]
    assert payload["label_counts"]["Person"] == 4
    text = format_schema(schema, "text")
    assert "Person" in text
    assert "4" in text
    assert "name" in text


def test_format_graphs():
    assert format_graphs(["a", "b"], "text") == "a\nb\n"
    assert json.loads(format_graphs(["a"], "json")) == ["a"]
    assert format_graphs([], "text") == ""
