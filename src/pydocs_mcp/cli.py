from __future__ import annotations

import json
from pathlib import Path

import typer

from .config import DEFAULT_DB_PATH, DEFAULT_SNAPSHOT_DIR, ensure_app_dirs, load_sources
from .indexer import index_sources
from .log import configure_logging
from .mcp_server import create_server
from .search import read_doc, search_docs
from .storage import SQLiteStore

app = typer.Typer(add_completion=False, help="Offline Python/ML docs MCP server")


def _expand_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path.expanduser()


@app.command()
def sources(config: Path | None = typer.Option(None, "--config", "-c")) -> None:
    """List configured documentation sources."""
    config = _expand_path(config)
    payload = [source.__dict__ for source in load_sources(config)]
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def index(
    config: Path | None = typer.Option(None, "--config", "-c"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db"),
    max_pages: int | None = typer.Option(None, "--max-pages"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch documentation and build the local index."""
    configure_logging(verbose)
    config = _expand_path(config)
    db = _expand_path(db) or db
    ensure_app_dirs([db.parent, DEFAULT_SNAPSHOT_DIR])

    sources = load_sources(config)
    summaries = index_sources(db_path=db, sources=sources, max_pages=max_pages)
    typer.echo(json.dumps([s.__dict__ for s in summaries], indent=2))


@app.command()
def search(
    query: str = typer.Argument(..., help="FTS query string"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db"),
    limit: int = typer.Option(10, "--limit"),
    source: str | None = typer.Option(None, "--source"),
) -> None:
    """Search the local index."""
    db = _expand_path(db) or db
    results = search_docs(db_path=db, query=query, limit=limit, source=source)
    typer.echo(json.dumps(results, indent=2))


@app.command()
def read(
    doc_id: int | None = typer.Option(None, "--id"),
    url: str | None = typer.Option(None, "--url"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db"),
) -> None:
    """Read a document by id or url."""
    db = _expand_path(db) or db
    if doc_id is None and url is None:
        raise typer.BadParameter("Provide --id or --url")
    record = read_doc(db_path=db, doc_id=doc_id, url=url)
    if record is None:
        raise typer.Exit(code=1)
    typer.echo(json.dumps(record.__dict__, indent=2))


@app.command()
def stats(db: Path = typer.Option(DEFAULT_DB_PATH, "--db")) -> None:
    """Show index statistics."""
    db = _expand_path(db) or db
    store = SQLiteStore(db)
    store.init_db()
    typer.echo(json.dumps(store.stats(), indent=2))


@app.command()
def serve(db: Path = typer.Option(DEFAULT_DB_PATH, "--db")) -> None:
    """Run MCP server over stdio (offline)."""
    db = _expand_path(db) or db
    ensure_app_dirs([db.parent])
    typer.echo(f"Starting MCP server with database at {db}", err=True)
    server = create_server(db)
    server.run(transport="stdio")
