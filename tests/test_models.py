from falkorterm.client.models import CellValue, ConnectionConfig, GraphSchema, QueryResult


def test_connection_config_defaults():
    cfg = ConnectionConfig()
    assert cfg.host == "localhost"
    assert cfg.port == 6379
    assert cfg.graph == "falkorterm"
    assert cfg.password is None
    assert cfg.timeout_ms == 30_000
    assert cfg.max_rows == 500
    assert cfg.read_only is False


def test_display_target():
    cfg = ConnectionConfig(host="db", port=6380, graph="social")
    assert cfg.display_target == "social@db:6380"


def test_graph_schema_immutable():
    schema = GraphSchema(labels=("Person",), relations=("KNOWS",))
    assert schema.labels == ("Person",)
    assert schema.relations == ("KNOWS",)
    assert schema.property_keys == ()
    assert schema.label_counts == ()


def test_query_result_defaults():
    result = QueryResult(columns=("n",), rows=((CellValue("1"),),))
    assert result.truncated is False
    assert result.total_rows == 0
    assert result.elapsed_ms is None


def test_query_result_elapsed_ms():
    result = QueryResult(
        columns=("n",),
        rows=((CellValue("1"),),),
        total_rows=1,
        elapsed_ms=12.5,
    )
    assert result.elapsed_ms == 12.5
