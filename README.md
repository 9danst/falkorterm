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

Al arrancar se abre la **pantalla de conexión**. Usa **Connect** para listar grafos y **Open** para entrar. Puedes guardar perfiles con nombre (host/port/password/graph/read-only); el perfil `default`, si existe, se aplica al abrir. Con `Ctrl+o` cambias de grafo o servidor sin reiniciar.

Marca **Read-only** (o `FALKOR_READ_ONLY=1`) para bloquear queries de escritura en el cliente (no es un ACL del servidor). Sin read-only, las escrituras (`CREATE`, `MERGE`, `DELETE`, etc.) piden confirmación. El editor sugiere labels/relaciones/propiedades del schema (aceptar con flecha derecha).

### Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `FALKOR_HOST` | `localhost` | Host (prefill) |
| `FALKOR_PORT` | `6379` | Puerto (prefill) |
| `FALKOR_GRAPH` | `falkorterm` | Nombre del grafo (prefill) |
| `FALKOR_PASSWORD` | _(vacío)_ | Password Redis/FalkorDB |
| `FALKOR_TIMEOUT_MS` | `30000` | Timeout de query (ms) |
| `FALKOR_MAX_ROWS` | `500` | Máximo de filas en la tabla |
| `FALKOR_READ_ONLY` | _(off)_ | `1`/`true`/`yes`/`on` → conexión solo lectura |
| `FALKOR_HISTORY_PATH` | _(XDG data)_ | Ruta del historial Cypher |
| `FALKOR_EXPORT_DIR` | _(XDG data)/exports_ | Directorio de exportación CSV/JSON |
| `FALKOR_PROFILES_PATH` | _(XDG data)/profiles.json_ | Perfiles de conexión guardados |

Las contraseñas de perfiles se almacenan en claro en el JSON (mismo riesgo que `.env`).

Ejemplo:

```bash
FALKOR_GRAPH=social FALKOR_HOST=127.0.0.1 uv run falkorterm
```

### Temas

El default es **flux-3** (fucsia / magenta / ámbar). También están `flux-1` (solo fucsia), `flux-2` (fucsia + cyan), `luan` (neón cyan/púrpura sobre negro), `rhodia` (negro/blanco + naranja Dotpad) y `falkorterm` (teal). Cámbialos con la Command Palette de Textual (`Ctrl+P` → *Change theme*).

### Atajos

| Tecla | Acción |
|-------|--------|
| `F1` / `Ctrl+1` | Foco en Context |
| `F2` / `Ctrl+2` | Foco en Results |
| `F3` / `Ctrl+3` | Foco en Query |
| `Ctrl+Enter` / `Ctrl+J` | Ejecutar Cypher |
| `Ctrl+o` | Abrir pantalla de conexión / cambiar grafo (en Surf: jump-back) |
| `Ctrl+e` | Exportar resultados (CSV o JSON) |
| `Ctrl+Shift+C` | Copiar query al portapapeles |
| `F4` / `Ctrl+Shift+H` (en Query) | Abrir cheatsheet Cypher (FalkorDB) |
| `Esc` | Cancelar query en curso (cierra conexión y reconecta) |
| `r` | Refrescar schema (o reabrir conexión si falló) |
| `q` | Salir |
| `y` / `Y` (en Results) | Copiar celda / fila (TSV) |
| `g` (en Results) | Ciclar tabla → grafo ASCII → Surf |
| `c` (en grafo/Surf, focus F2) | Copiar diagrama ASCII o Surf al portapapeles |
| `Enter` (en Context) | Insertar plantilla MATCH / propiedad en el editor |
| `c` (en Context) | Insertar plantilla `count` del label/relación enfocado |
| `Enter` (en Results) | Inspeccionar celda / nodo |
| `x` (detail / grafo) | Expandir vecinos del nodo (inserta Cypher y ejecuta) |
| `j`/`k`, `l`, `h`/`Ctrl+o`, `L`, `Tab` (en Surf) | Mover cursor, saltar, volver/avanzar historial y alternar nodo/arista |

Surf es un inspector ego-hop denso (caja FOCUS, OUT/IN alineados, panel `selected`, hints contextuales); no pinta el grafo completo en ASCII.

Para pegar fuera del terminal en Wayland hace falta [`wl-clipboard`](https://github.com/bugaevc/wl-clipboard) (`wl-copy`); en X11, `xclip` o `xsel`. Sin eso, OSC 52 suele fallar (p. ej. en Cursor).

## Tests

```bash
uv run pytest -v
```

## Layout

- **Context** (izquierda): labels, relaciones, property keys
- **Results** (arriba derecha): tabla de resultados, grafo ASCII o Surf (`g`), o errores
- **Query** (abajo derecha): editor Cypher
