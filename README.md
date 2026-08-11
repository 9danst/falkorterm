# FalkorTerm

TUI client ([Textual](https://textual.textualize.io/)) for [FalkorDB](https://www.falkordb.com/): explore labels and relationships, write Cypher, and view results as a table or graph.

![FalkorTerm screenshot](docs/assets/screenshot-1.svg)

## Requirements

- Python ≥ 3.12
- Docker (optional, for a local FalkorDB)
- A reachable FalkorDB instance (default `localhost:6379`)

## Installation

```bash
uv sync --extra dev
cp .env.example .env   # if you do not already have a .env
```

## Local FalkorDB (Docker)

```bash
docker compose up -d --build
```

- Server: `localhost:6379`
- Browser UI: http://localhost:3000

```bash
docker compose down          # stop
docker compose down -v       # stop and wipe data
```

## Usage

Load variables from `.env` (they prefill the connection screen) and start the TUI:

```bash
set -a && source .env && set +a
uv run falkorterm
# or
uv run python -m falkorterm
```

On launch you get the **connection screen**. Use **Connect** to list graphs and **Open** to enter one. You can save named profiles (host/port/password/graph/read-only); if a `default` profile exists, it is applied on open. Press `Ctrl+o` to switch graph or server without restarting.

Enable **Read-only** (or `FALKOR_READ_ONLY=1`) to block write queries in the client (this is not a server ACL). Without read-only, writes (`CREATE`, `MERGE`, `DELETE`, etc.) ask for confirmation. The editor suggests labels/relationships/properties from the schema (accept with the right arrow).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKOR_HOST` | `localhost` | Host (prefill) |
| `FALKOR_PORT` | `6379` | Port (prefill) |
| `FALKOR_GRAPH` | `falkorterm` | Graph name (prefill) |
| `FALKOR_PASSWORD` | _(empty)_ | Redis/FalkorDB password |
| `FALKOR_TIMEOUT_MS` | `30000` | Query timeout (ms) |
| `FALKOR_MAX_ROWS` | `500` | Max rows in the results table |
| `FALKOR_READ_ONLY` | _(off)_ | `1`/`true`/`yes`/`on` → read-only connection |
| `FALKOR_HISTORY_PATH` | _(XDG data)_ | Cypher history path |
| `FALKOR_EXPORT_DIR` | _(XDG data)/exports_ | CSV/JSON export directory |
| `FALKOR_PROFILES_PATH` | _(XDG data)/profiles.json_ | Saved connection profiles |

Profile passwords are stored in plain text in the JSON (same risk as `.env`).

Example:

```bash
FALKOR_GRAPH=social FALKOR_HOST=127.0.0.1 uv run falkorterm
```

### Themes

The default is **flux-3** (fuchsia / magenta / amber). Also available: `flux-1` (fuchsia only), `flux-2` (fuchsia + cyan), `luan` (neon cyan/purple on black), `rhodia` (black/white + Dotpad orange), and `falkorterm` (teal). Switch themes with Textual’s Command Palette (`Ctrl+P` → *Change theme*).

### Shortcuts

| Key | Action |
|-----|--------|
| `F1` / `Ctrl+1` | Focus Context |
| `F2` / `Ctrl+2` | Focus Results |
| `F3` / `Ctrl+3` | Focus Query |
| `Ctrl+Enter` / `Ctrl+J` | Run Cypher |
| `Ctrl+o` | Open connection screen / switch graph (in Surf: jump back) |
| `Ctrl+e` | Export results (CSV or JSON) |
| `Ctrl+Shift+C` | Copy query to clipboard |
| `F4` / `Ctrl+Shift+H` (in Query) | Open Cypher cheatsheet (FalkorDB) |
| `Esc` | Cancel in-flight query (closes connection and reconnects) |
| `r` | Refresh schema (or reopen connection if it failed) |
| `q` | Quit |
| `y` / `Y` (in Results) | Copy cell / row (TSV) |
| `g` (in Results) | Cycle table → ASCII graph → Surf |
| `c` (in graph/Surf, F2 focused) | Copy ASCII diagram or Surf to clipboard |
| `Enter` (in Context) | Insert MATCH / property template into the editor |
| `c` (in Context) | Insert `count` template for the focused label/relationship |
| `Enter` (in Results) | Inspect cell / node |
| `x` (detail / graph) | Expand node neighbors (inserts Cypher and runs it) |
| `j`/`k`, `l`, `h`/`Ctrl+o`, `L`, `Tab` (in Surf) | Move cursor, jump, history back/forward, toggle node/edge |

Surf is a dense ego-hop inspector (FOCUS box, aligned OUT/IN, `selected` panel, contextual hints); it does not draw the full graph in ASCII.

To paste outside the terminal on Wayland you need [`wl-clipboard`](https://github.com/bugaevc/wl-clipboard) (`wl-copy`); on X11, `xclip` or `xsel`. Without that, OSC 52 often fails (e.g. in Cursor).

## Tests

```bash
uv run pytest -v
```

## Layout

- **Context** (left): labels, relationships, property keys
- **Results** (top right): results table, ASCII graph or Surf (`g`), or errors
- **Query** (bottom right): Cypher editor
