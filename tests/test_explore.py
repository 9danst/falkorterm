from falkorterm.explore import (
    count_label_cypher,
    count_relation_cypher,
    neighbors_cypher,
)


def test_neighbors_cypher():
    assert neighbors_cypher(42) == (
        "MATCH (n)-[r]-(m) WHERE id(n) = 42 RETURN n, r, m LIMIT 50"
    )


def test_count_label_cypher():
    assert count_label_cypher("Person") == "MATCH (n:Person) RETURN count(n) AS count"


def test_count_relation_cypher():
    assert (
        count_relation_cypher("KNOWS")
        == "MATCH ()-[r:KNOWS]->() RETURN count(r) AS count"
    )
