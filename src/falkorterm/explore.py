from __future__ import annotations

from textual.message import Message


class ExpandNeighborsRequested(Message):
    """User asked to expand neighbors of a node by internal id."""

    def __init__(self, node_id: int) -> None:
        super().__init__()
        self.node_id = node_id


def neighbors_cypher(node_id: int) -> str:
    return (
        f"MATCH (n)-[r]-(m) WHERE id(n) = {int(node_id)} "
        "RETURN n, r, m LIMIT 50"
    )


def count_label_cypher(label: str) -> str:
    return f"MATCH (n:{label}) RETURN count(n) AS count"


def count_relation_cypher(relation: str) -> str:
    return f"MATCH ()-[r:{relation}]->() RETURN count(r) AS count"
