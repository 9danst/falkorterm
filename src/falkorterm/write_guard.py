from __future__ import annotations

import re

_WRITE_RE = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH)\b",
    re.IGNORECASE,
)
_LINE_COMMENT_RE = re.compile(r"//.*?$", re.MULTILINE)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_cypher_comments(cypher: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(" ", cypher)
    text = _LINE_COMMENT_RE.sub(" ", text)
    return text


def is_write_query(cypher: str) -> bool:
    """Heuristic: True if Cypher appears to mutate the graph."""
    cleaned = strip_cypher_comments(cypher)
    return _WRITE_RE.search(cleaned) is not None
