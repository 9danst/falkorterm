import pytest

from falkorterm.write_guard import is_write_query, strip_cypher_comments


@pytest.mark.parametrize(
    ("cypher", "expected"),
    [
        ("MATCH (n) RETURN n", False),
        ("RETURN 1", False),
        ("CALL db.labels()", False),
        ("CREATE (n:Person)", True),
        ("MERGE (n:Person {id: 1})", True),
        ("MATCH (n) DELETE n", True),
        ("MATCH (n) SET n.x = 1", True),
        ("MATCH (n) REMOVE n.x", True),
        ("DROP INDEX ON :Person(name)", True),
        ("MATCH (n) DETACH DELETE n", True),
        ("// CREATE (n)\nMATCH (n) RETURN n", False),
        ("/* MERGE (n) */ RETURN 1", False),
        ("match (n) create (m) return m", True),
    ],
)
def test_is_write_query(cypher: str, expected: bool):
    assert is_write_query(cypher) is expected


def test_strip_cypher_comments():
    assert "CREATE" not in strip_cypher_comments("// CREATE\nRETURN 1")
    assert "MERGE" not in strip_cypher_comments("/* MERGE */ RETURN 1")
