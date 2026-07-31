# FalkorTerm

Cliente TUI (Textual) para [FalkorDB](https://www.falkordb.com/): explorar labels y relaciones, escribir Cypher y ver resultados en tabla.

## Requisitos

- Python ≥ 3.12
- Docker (opcional, para FalkorDB local)
- Una instancia de FalkorDB accesible (por defecto `localhost:6379`)

## Instalación

```bash
uv sync --extra dev
cp .env.example .env   # si aún no tienes .env
```

## FalkorDB local (Docker)

```bash
docker compose up -d --build
```

- Servidor: `localhost:6379`
- Browser UI: http://localhost:3000

```bash
docker compose down          # parar
docker compose down -v       # parar y borrar datos
```

## Uso

Carga las variables del `.env` (pre-rellenan la pantalla de conexión) y arranca la TUI:

```bash
set -a && source .env && set +a
uv run falkorterm
# o
uv run python -m falkorterm
```

Al arrancar se abre la **pantalla de conexión**. Usa **Connect** para listar grafos y **Open** para entrar. Puedes guardar perfiles con nombre (host/port/password/graph); el perfil `default`, si existe, se aplica al abrir. Con `Ctrl+o` cambias de grafo o servidor sin reiniciar.

Las queries de escritura (`CREATE`, `MERGE`, `DELETE`, etc.) piden confirmación antes de ejecutarse. El editor sugiere labels/relaciones/propiedades del schema (aceptar con flecha derecha).

### Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `FALKOR_HOST` | `localhost` | Host (prefill) |
| `FALKOR_PORT` | `6379` | Puerto (prefill) |
| `FALKOR_GRAPH` | `falkorterm` | Nombre del grafo (prefill) |
| `FALKOR_PASSWORD` | _(vacío)_ | Password Redis/FalkorDB |
| `FALKOR_TIMEOUT_MS` | `30000` | Timeout de query (ms) |
| `FALKOR_MAX_ROWS` | `500` | Máximo de filas en la tabla |
| `FALKOR_HISTORY_PATH` | _(XDG data)_ | Ruta del historial Cypher |
| `FALKOR_EXPORT_DIR` | _(XDG data)/exports_ | Directorio de exportación CSV/JSON |
| `FALKOR_PROFILES_PATH` | _(XDG data)/profiles.json_ | Perfiles de conexión guardados |

Las contraseñas de perfiles se almacenan en claro en el JSON (mismo riesgo que `.env`).

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
| `Ctrl+Enter` / `Ctrl+J` | Ejecutar Cypher |
| `Ctrl+o` | Abrir pantalla de conexión / cambiar grafo |
| `Ctrl+e` | Exportar resultados (CSV o JSON) |
| `Ctrl+Shift+C` | Copiar query al portapapeles |
| `Esc` | Cancelar query en curso (cierra conexión y reconecta) |
| `r` | Refrescar schema (o reabrir conexión si falló) |
| `q` | Salir |
| `y` / `Y` (en Results) | Copiar celda / fila (TSV) |
| `Enter` (en Context) | Insertar plantilla Cypher / propiedad en el editor |
| `Enter` (en Results) | Inspeccionar celda / nodo |

## Tests

```bash
uv run pytest -v
```

## Layout

- **Context** (izquierda): labels, relaciones, property keys
- **Results** (arriba derecha): tabla de resultados o errores
- **Query** (abajo derecha): editor Cypher
