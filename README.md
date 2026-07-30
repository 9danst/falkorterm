# FalkorTerm

Cliente TUI (Textual) para [FalkorDB](https://www.falkordb.com/): explorar labels y relaciones, escribir Cypher y ver resultados en tabla.

## Requisitos

- Python ≥ 3.12
- Una instancia de FalkorDB accesible (por defecto `localhost:6379`)

## Instalación

```bash
uv sync --extra dev
```

## Uso

```bash
uv run falkorterm
# o
uv run python -m falkorterm
```

### Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `FALKOR_HOST` | `localhost` | Host |
| `FALKOR_PORT` | `6379` | Puerto |
| `FALKOR_GRAPH` | `falkorterm` | Nombre del grafo |
| `FALKOR_PASSWORD` | _(vacío)_ | Password Redis/FalkorDB |
| `FALKOR_TIMEOUT_MS` | `30000` | Timeout de query (ms) |
| `FALKOR_MAX_ROWS` | `500` | Máximo de filas en la tabla |

Ejemplo:

```bash
FALKOR_GRAPH=social FALKOR_HOST=127.0.0.1 uv run falkorterm
```

### Atajos

| Tecla | Acción |
|-------|--------|
| `Ctrl+1` | Foco en Context |
| `Ctrl+2` | Foco en Results |
| `Ctrl+3` | Foco en Query |
| `Ctrl+Enter` | Ejecutar Cypher |
| `r` | Refrescar schema (o reintentar conexión) |
| `q` | Salir |
| `Enter` (en Context) | Insertar plantilla Cypher en el editor |

## Tests

```bash
uv run pytest -v
```

## Layout

- **Context** (izquierda): labels y tipos de relación
- **Results** (arriba derecha): tabla de resultados o errores
- **Query** (abajo derecha): editor Cypher
