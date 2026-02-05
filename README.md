# pydocs-mcp

Offline Python and ML documentation as an MCP server. This mirrors the layering from the Cupertino project but targets Python, NumPy, Pandas, PyTorch, and other ML libraries.

## Cupertino architecture notes (from README)

Cupertino is organized as a multi-package Swift workspace with clear layers:

- **Foundation layer**: shared utilities like MCP support, logging, and shared types.
- **Infrastructure layer**: core crawling/downloading and search/indexing (SQLite FTS5).
- **Application layer**: the MCP server and CLI that expose the capabilities.

This project keeps the same separation but in Python.

## Python architecture mapping

- **Foundation**: `config.py`, `log.py`, `parser.py` (shared config, logging, HTML to Markdown).
- **Infrastructure**: `crawler.py` and `storage.py` (fetching + SQLite FTS5 storage).
- **Application**: `indexer.py` and `search.py` (orchestration and query API).
- **Interface**: `cli.py` and `mcp_server.py` (CLI + MCP tools).

## Quick start (uv)

```bash
uv sync
uv run pydocs-mcp sources
uv run pydocs-mcp index --max-pages 200
uv run pydocs-mcp search "list comprehension"
```

Default database path: `~/.pydocs_mcp/docs.db`
Environment overrides: `PYDOCS_HOME` and `PYDOCS_DB`

## MCP server (offline)

```bash
uv run pydocs-mcp serve --db ~/.pydocs_mcp/docs.db
```

Note: the MCP server runs over stdio, so the command will appear idle while it waits for a client connection.

The server only reads the local SQLite database. No network calls are made while serving.

### VSCode MCP config

See `.vscode/mcp.json` and update the `--db` path to your local database. The sample config uses `${env:HOME}` so it should work across machines.

## Configuration

Default sources live in `src/pydocs_mcp/data/sources.yaml`. You can override with:

```bash
uv run pydocs-mcp index --config /path/to/sources.yaml
```

Each source supports:

- `start_urls`
- `allowed_domains`
- `include_patterns` and `exclude_patterns`
- `max_pages` and `crawl_delay_seconds`

## Expanded ML sources

The default `sources.yaml` now includes a broader set of Python ML libraries pulled from the Python section of the awesome-machine-learning list (core ML, CV, and NLP). The full list is in `src/pydocs_mcp/data/sources.yaml`.

## MCP tools

- `search_docs(query, limit=10, source=None)`
- `read_doc(doc_id=None, url=None)`
- `list_sources()`
- `get_stats()`
