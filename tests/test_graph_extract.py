from falkorterm.client.models import CellValue, QueryResult
from falkorterm.graph.extract import extract_graph


def _node(nid: int, label: str = "Person") -> CellValue:
    return CellValue(
        display=f"(:{label} id={nid})",
        detail={
            "kind": "node",
            "id": nid,
            "labels": [label],
            "properties": {},
        },
    )


def _edge(src: int, dest: int, rel: str = "KNOWS", eid: int | None = None) -> CellValue:
    detail: dict[str, object] = {
        "kind": "edge",
        "type": rel,
        "src": src,
        "dest": dest,
        "properties": {},
    }
    if eid is not None:
        detail["id"] = eid
    return CellValue(display=f"-[:{rel}]->", detail=detail)


def test_extract_triple():
    result = QueryResult(
        columns=("a", "r", "b"),
        rows=((_node(1), _edge(1, 2, eid=9), _node(2)),),
        total_rows=1,
    )
    model = extract_graph(result)
    assert len(model.nodes) == 2
    assert len(model.edges) == 1
    assert model.edges[0].type == "KNOWS"
    assert model.edges[0].src == 1
    assert model.edges[0].dest == 2
    assert model.truncated is False


def test_extract_path_cell():
    result = QueryResult(
        columns=("p",),
        rows=(
            (
                CellValue(
                    display="<path 2 nodes>",
                    detail={
                        "kind": "path",
                        "nodes": [
                            {
                                "kind": "node",
                                "id": 1,
                                "labels": ["Person"],
                                "properties": {},
                            },
                            {
                                "kind": "node",
                                "id": 2,
                                "labels": ["Person"],
                                "properties": {},
                            },
                        ],
                        "edges": [
                            {
                                "kind": "edge",
                                "type": "KNOWS",
                                "src": 1,
                                "dest": 2,
                                "id": 9,
                                "properties": {},
                            }
                        ],
                    },
                ),
            ),
        ),
        total_rows=1,
    )
    model = extract_graph(result)
    assert {n.id for n in model.nodes} == {1, 2}
    assert len(model.edges) == 1


def test_extract_scalars_empty():
    result = QueryResult(
        columns=("n",),
        rows=((CellValue(display="1"),),),
        total_rows=1,
    )
    model = extract_graph(result)
    assert model.nodes == ()
    assert model.edges == ()


def test_extract_truncates_nodes():
    rows = tuple((_node(i),) for i in range(30))
    result = QueryResult(columns=("n",), rows=rows, total_rows=30)
    model = extract_graph(result, max_nodes=25, max_edges=40)
    assert len(model.nodes) == 25
    assert model.total_nodes == 30
    assert model.truncated is True
