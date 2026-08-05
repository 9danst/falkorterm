# Cypher cheatsheet (FalkorDB)

OpenCypher subset used by FalkorDB. Examples are illustrative.

## Reading

```cypher
MATCH (n:Person)
WHERE n.name STARTS WITH 'A'
RETURN n
ORDER BY n.name
SKIP 0 LIMIT 25
```

```cypher
OPTIONAL MATCH (a:Person)-[r:KNOWS]->(b)
RETURN a, r, b
```

```cypher
MATCH (n:Person)
WITH n, size([(n)--() | 1]) AS degree
WHERE degree > 1
RETURN n.name, degree
ORDER BY degree DESC
```

```cypher
UNWIND [1, 2, 3] AS x
RETURN x
```

## Writing

```cypher
CREATE (a:Person {name: 'Ada'})-[:KNOWS]->(b:Person {name: 'Bob'})
```

```cypher
MERGE (n:Person {name: 'Ada'})
ON CREATE SET n.created = timestamp()
ON MATCH SET n.seen = timestamp()
RETURN n
```

```cypher
MATCH (n:Person {name: 'Ada'})
SET n.age = 36
REMOVE n.temp
RETURN n
```

```cypher
MATCH (n:Person {name: 'Tmp'})
DETACH DELETE n
```

## Patterns & aggregations

```cypher
MATCH (a:Person)-[:KNOWS*1..2]->(b:Person)
WHERE a <> b
RETURN DISTINCT b.name
```

```cypher
MATCH (n:Person)-[r:KNOWS]->()
RETURN n.name, count(r) AS friends
ORDER BY friends DESC
```

```cypher
MATCH (n:Person)
RETURN collect(n.name) AS names, sum(n.age) AS ages
```

String filters: `STARTS WITH`, `ENDS WITH`, `CONTAINS` (no regex `=~`).

## Procedures (schema)

```cypher
CALL db.labels()
CALL db.relationshipTypes()
CALL db.propertyKeys()
```

## Limitations (vs Neo4j)

- No regex operator; use string predicates above.
- No APOC / Neo4j GDS library.
- Label expressions and some newer Cypher features may be missing.
- `LIMIT` does not truncate eager writes (`CREATE`/`SET`/`DELETE`/`MERGE`) — they still run fully.
- Prefer referencing relationship variables when you need every match counted.
