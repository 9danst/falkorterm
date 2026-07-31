from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from falkorterm.client.falkor import FalkorClient
from falkorterm.client.models import (
    CellValue,
    ConnectionConfig,
    FalkorConnectionError,
    FalkorQueryError,
)


def _make_raw(header, rows):
    return SimpleNamespace(header=header, result_set=rows)


@pytest.fixture
def connected_client():
    client = FalkorClient()
    config = ConnectionConfig(max_rows=2, timeout_ms=5000)
    graph = MagicMock()
    client._graph = graph
    client._config = config
    client._db = MagicMock()
    return client, graph


def test_run_query_maps_and_truncates(connected_client):
    client, graph = connected_client
    graph.query.return_value = _make_raw(
        ["name", "age"],
        [["Ada", 36], ["Bob", 40], ["Cyd", 22]],
    )
    result = client.run_query("MATCH (n) RETURN n.name, n.age")
    assert result.columns == ("name", "age")
    assert result.rows == (
        (CellValue("Ada"), CellValue("36")),
        (CellValue("Bob"), CellValue("40")),
    )
    assert result.truncated is True
    assert result.total_rows == 3
    assert result.elapsed_ms is not None
    assert result.elapsed_ms >= 0
    graph.query.assert_called_once_with(
        "MATCH (n) RETURN n.name, n.age", timeout=5000
    )


def test_run_query_parses_typed_headers(connected_client):
    client, graph = connected_client
    graph.query.return_value = _make_raw(
        [[1, "name"], [2, "age"]],
        [["Ada", 36]],
    )
    result = client.run_query("RETURN 1")
    assert result.columns == ("name", "age")
    assert result.rows == ((CellValue("Ada"), CellValue("36")),)


def test_run_query_serializes_complex_cells(connected_client):
    client, graph = connected_client
    node = SimpleNamespace(labels=["Person"], properties={"x": 1}, id=7)
    graph.query.return_value = _make_raw(["n"], [[node]])
    result = client.run_query("MATCH (n) RETURN n")
    cell = result.rows[0][0]
    assert isinstance(cell, CellValue)
    assert "Person" in cell.display
    assert cell.detail is not None
    assert cell.detail["kind"] == "node"
    assert cell.detail["properties"] == {"x": 1}


def test_run_query_maps_sdk_error(connected_client):
    client, graph = connected_client
    graph.query.side_effect = RuntimeError("syntax error")
    with pytest.raises(FalkorQueryError, match="syntax error"):
        client.run_query("NOT CYPHER")


def test_get_schema(connected_client):
    client, graph = connected_client

    def query_side_effect(cypher, timeout=None):
        if "labels()" in cypher:
            return _make_raw(["label"], [["Person"], ["Movie"]])
        if "relationshipTypes" in cypher:
            return _make_raw(["rel"], [["KNOWS"]])
        if "propertyKeys" in cypher:
            return _make_raw(["key"], [["name"], ["age"]])
        if "UNWIND labels" in cypher:
            return _make_raw(["l", "c"], [["Person", 3], ["Movie", 2]])
        if "type(r)" in cypher:
            return _make_raw(["t", "c"], [["KNOWS", 5]])
        raise AssertionError(cypher)

    graph.query.side_effect = query_side_effect
    schema = client.get_schema()
    assert schema.labels == ("Person", "Movie")
    assert schema.relations == ("KNOWS",)
    assert schema.property_keys == ("name", "age")
    assert schema.label_counts == (("Person", 3), ("Movie", 2))
    assert schema.relation_counts == (("KNOWS", 5),)


def test_connect_failure():
    client = FalkorClient()
    with patch("falkorterm.client.falkor.FalkorDB") as mock_db:
        mock_db.side_effect = OSError("refused")
        with pytest.raises(FalkorConnectionError, match="refused"):
            client.connect(ConnectionConfig())


def test_connect_success():
    client = FalkorClient()
    with patch("falkorterm.client.falkor.FalkorDB") as mock_db_cls:
        instance = MagicMock()
        instance.list_graphs.return_value = []
        instance.select_graph.return_value = MagicMock()
        mock_db_cls.return_value = instance
        client.connect(ConnectionConfig(graph="g1"))
        assert client.connected
        instance.select_graph.assert_called_once_with("g1")


def test_list_graphs(connected_client):
    client, _graph = connected_client
    client._db.list_graphs.return_value = ["a", "b"]
    assert client.list_graphs() == ["a", "b"]


def test_list_graphs_requires_db():
    client = FalkorClient()
    with pytest.raises(FalkorConnectionError, match="Not connected"):
        client.list_graphs()


def test_select_graph(connected_client):
    client, _graph = connected_client
    new_graph = MagicMock()
    client._db.select_graph.return_value = new_graph
    client.select_graph("other")
    assert client._graph is new_graph
    assert client.config is not None
    assert client.config.graph == "other"
    client._db.select_graph.assert_called_with("other")


def test_abort_and_reconnect(connected_client):
    client, _graph = connected_client
    old_db = client._db
    config = client._config
    assert config is not None

    with patch.object(client, "connect") as mock_connect:
        client.abort_and_reconnect()
        old_db.close.assert_called_once()
        assert client._db is None
        assert client._graph is None
        mock_connect.assert_called_once_with(config)
