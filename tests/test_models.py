from falkorterm.client.models import ConnectionConfig, GraphSchema, QueryResult


def test_connection_config_defaults():
    cfg = ConnectionConfig()
    assert cfg.host == "localhost"
    assert cfg.port == 6379
    assert cfg.graph == "falkorterm"
    assert cfg.password is None
    assert cfg.timeout_ms == 30_000
    assert cfg.max_rows == 500


def test_display_target():
    cfg = ConnectionConfig(host="db", port=6380, graph="social")
    assert cfg.display_target == "social@db:6380"


def test_graph_schema_immutable():
    schema = GraphSchema(labels=("Person",), relations=("KNOWS",))
    assert schema.labels == ("Person",)
    assert schema.relations == ("KNOWS",)


def test_query_result_defaults():
    result = QueryResult(columns=("n",), rows=((1,),))
    assert result.truncated is False
    assert result.total_rows == 0
