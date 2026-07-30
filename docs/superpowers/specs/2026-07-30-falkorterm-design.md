# FalkorTerm — Design Spec (MVP)

**Date:** 2026-07-30  
**Status:** Approved

## Summary

Terminal client (Textual + Rich) for FalkorDB: browse entities/relations, write Cypher, view tabular results. Graph view deferred to a later phase.

## Architecture

**Option B — Widgets + services:** UI widgets communicate via Textual messages; `FalkorClient` wraps the `falkordb` SDK; `FalkorTerm` app coordinates async workers. No direct DB calls from widgets.

## Layout

```
┌─────────────┬──────────────────────────────┐
│ ContextWidget│       ResultsWidget          │
│ Entities &  │       (table only in MVP)     │
│ Relations   ├───────────────────────────────┤
│             │       QueryWidget             │
│             │       (Cypher editor)         │
└─────────────┴───────────────────────────────┘
```

## Components

| Component | Role |
|-----------|------|
| `ContextWidget` | Sidebar: labels & relation types from schema |
| `ResultsWidget` | Tabular results (`DataTable`) or error text |
| `QueryWidget` | Cypher `TextArea`; in-memory history |
| `FalkorClient` | connect, get_schema, run_query |
| `FalkorTerm` | Message routing, workers, connection lifecycle |

## Messages

- `QuerySubmitted(cypher: str)`
- `SchemaItemSelected(kind: "label"|"relation", name: str)`

## UX bindings

- `ctrl+1/2/3` — focus Context / Results / Query
- `ctrl+enter` — run query
- `r` — refresh schema (and reconnect attempt on failure path)
- `q` — quit
- Enter on schema item — insert Cypher template into Query and focus it

### Templates

- Label `X` → `MATCH (n:X) RETURN n LIMIT 25`
- Relation `R` → `MATCH ()-[r:R]->() RETURN r LIMIT 25`

## Constraints (MVP)

- Connection via env/CLI only (no connection screen)
- Query timeout default 30s
- Max 500 rows displayed (truncate + notice)
- Cypher history in memory only
- No graph ASCII view

## Out of scope

- `GraphResultView` / table↔graph toggle
- Persistent history, multi-graph picker UI, in-place node editing
