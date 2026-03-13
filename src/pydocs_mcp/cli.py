from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer

from .config import (
    DEFAULT_APP_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_PACKAGES_CONFIG,
    DEFAULT_SNAPSHOT_DIR,
    PackageConfig,
    ensure_app_dirs,
    load_external_packages,
    load_sources,
    packages_to_sources,
    create_sample_packages_config,
)
from .indexer import index_sources
from .log import configure_logging
from .mcp_server import create_server
from .search import read_doc, search_docs
from .storage import SQLiteStore

app = typer.Typer(add_completion=False, help="Offline Python documentation MCP server")

FormatOption = Literal["json", "text"]


def _expand_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path.expanduser()


@app.command()
def setup(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Custom sources config"),
    packages_config: Path | None = typer.Option(None, "--packages-config", "-p", help="External packages config"),
    max_pages: int | None = typer.Option(None, "--max-pages", "-m", help="Max pages per source"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Quick setup: download docs and build index in one step."""
    configure_logging(verbose)
    db = _expand_path(db) or db
    config = _expand_path(config)
    packages_config = _expand_path(packages_config)
    
    ensure_app_dirs([db.parent, DEFAULT_SNAPSHOT_DIR])
    
    # Load built-in sources
    sources = load_sources(config)
    
    # Load external packages if config exists
    external_packages = load_external_packages(packages_config)
    if external_packages:
        typer.echo(f"Found {len(external_packages)} external package(s) to index", err=True)
        sources.extend(packages_to_sources(external_packages))
    
    # Index all sources
    summaries = index_sources(db_path=db, sources=sources, max_pages=max_pages)
    
    typer.echo(json.dumps([s.__dict__ for s in summaries], indent=2))


@app.command()
def fetch(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Custom sources config"),
    packages_config: Path | None = typer.Option(None, "--packages-config", "-p", help="External packages config"),
    source: str | None = typer.Option(None, "--source", "-s", help="Fetch only specific source"),
    max_pages: int | None = typer.Option(None, "--max-pages", "-m", help="Max pages per source"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Download documentation from configured sources."""
    configure_logging(verbose)
    db = _expand_path(db) or db
    config = _expand_path(config)
    packages_config = _expand_path(packages_config)
    
    ensure_app_dirs([db.parent, DEFAULT_SNAPSHOT_DIR])
    
    # Load built-in sources
    sources = load_sources(config)
    
    # Filter by source name if specified
    if source:
        sources = [s for s in sources if s.name == source]
        if not sources:
            typer.echo(f"Error: Source '{source}' not found", err=True)
            raise typer.Exit(code=1)
    
    # Load external packages if config exists
    external_packages = load_external_packages(packages_config)
    if external_packages:
        external_sources = packages_to_sources(external_packages)
        if source:
            external_sources = [s for s in external_sources if s.name == source]
        sources.extend(external_sources)
    
    # Index all sources
    summaries = index_sources(db_path=db, sources=sources, max_pages=max_pages)
    
    typer.echo(json.dumps([s.__dict__ for s in summaries], indent=2))


@app.command(name="save")
def save_cmd(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Build or refresh the search index (alias for rebuild)."""
    configure_logging(verbose)
    db = _expand_path(db) or db
    
    store = SQLiteStore(db)
    store.init_db()
    stats = store.stats()
    
    typer.echo(json.dumps({
        "status": "Index ready",
        "database": str(db),
        "documents": stats["documents"],
        "sources": store.list_sources()
    }, indent=2))


@app.command()
def serve(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
) -> None:
    """Run MCP server over stdio (offline)."""
    db = _expand_path(db) or db
    ensure_app_dirs([db.parent])
    typer.echo(f"Starting MCP server with database at {db}", err=True)
    server = create_server(db)
    server.run(transport="stdio")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    source: str | None = typer.Option(None, "--source", "-s", help="Filter by source"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
    format: FormatOption = typer.Option("json", "--format", "-f", help="Output format"),
) -> None:
    """Search the documentation index."""
    db = _expand_path(db) or db
    results = search_docs(db_path=db, query=query, limit=limit, source=source)
    
    if format == "json":
        typer.echo(json.dumps(results, indent=2))
    else:
        if not results:
            typer.echo("No results found.")
            return
        typer.echo(f"Found {len(results)} result(s) for '{query}':\n")
        for i, r in enumerate(results, 1):
            typer.echo(f"{i}. {r['title']}")
            typer.echo(f"   Source: {r['source']}")
            typer.echo(f"   URL: {r['url']}")
            if r.get('snippet'):
                typer.echo(f"   {r['snippet']}")
            typer.echo()


@app.command()
def read(
    doc_id: int | None = typer.Option(None, "--id", "-i", help="Document ID"),
    url: str | None = typer.Option(None, "--url", "-u", help="Document URL"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    format: FormatOption = typer.Option("json", "--format", "-f", help="Output format"),
) -> None:
    """Read a document by ID or URL."""
    db = _expand_path(db) or db
    
    if doc_id is None and url is None:
        typer.echo("Error: Provide --id or --url", err=True)
        raise typer.Exit(code=1)
    
    record = read_doc(db_path=db, doc_id=doc_id, url=url)
    
    if record is None:
        typer.echo("Error: Document not found", err=True)
        raise typer.Exit(code=1)
    
    if format == "json":
        typer.echo(json.dumps(record.__dict__, indent=2))
    else:
        typer.echo(f"Title: {record.title}")
        typer.echo(f"Source: {record.source}")
        typer.echo(f"URL: {record.url}")
        typer.echo(f"Fetched: {record.fetched_at}")
        typer.echo(f"\n{record.content}")


@app.command(name="list-sources")
def list_sources_cmd(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    format: FormatOption = typer.Option("json", "--format", "-f", help="Output format"),
) -> None:
    """List configured documentation sources."""
    db = _expand_path(db) or db
    store = SQLiteStore(db)
    store.init_db()
    sources = store.list_sources()
    
    if format == "json":
        typer.echo(json.dumps(sources, indent=2))
    else:
        if not sources:
            typer.echo("No sources found.")
            return
        typer.echo(f"{'Source':<20} {'Documents':>10}")
        typer.echo("-" * 32)
        for s in sources:
            typer.echo(f"{s['source']:<20} {s['count']:>10}")


@app.command()
def stats(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d", help="Database path"),
    format: FormatOption = typer.Option("json", "--format", "-f", help="Output format"),
) -> None:
    """Show index statistics."""
    db = _expand_path(db) or db
    store = SQLiteStore(db)
    store.init_db()
    stats_data = store.stats()
    sources = store.list_sources()
    
    result = {
        **stats_data,
        "database": str(db),
        "sources": sources,
    }
    
    if format == "json":
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(f"Database: {result['database']}")
        typer.echo(f"Total documents: {result['documents']}")
        typer.echo(f"Sources: {len(sources)}")
        if sources:
            typer.echo("\nBreakdown by source:")
            for s in sources:
                typer.echo(f"  - {s['source']}: {s['count']} documents")


@app.command()
def packages(
    action: str = typer.Argument(..., help="Action: init, list, add"),
    path: Path = typer.Option(DEFAULT_PACKAGES_CONFIG, "--path", "-p", help="Packages config path"),
    name: str | None = typer.Option(None, "--name", "-n", help="Package name (for add)"),
    url: str | None = typer.Option(None, "--url", "-u", help="Documentation URL (for add)"),
) -> None:
    """Manage external package documentation configuration."""
    path = _expand_path(path) or path
    
    if action == "init":
        if path.exists():
            typer.echo(f"Config already exists at {path}", err=True)
            raise typer.Exit(code=1)
        ensure_app_dirs([path.parent])
        create_sample_packages_config(path)
        typer.echo(f"Created sample packages config at {path}")
        typer.echo("Edit this file to add your own packages, then run: pydocs-mcp fetch")
    
    elif action == "list":
        packages = load_external_packages(path)
        if not packages:
            typer.echo("No external packages configured.")
            typer.echo(f"Create a config with: pydocs-mcp packages init")
            return
        typer.echo(json.dumps([{
            "name": p.name,
            "doc_url": p.doc_url,
            "doc_type": p.doc_type,
            "max_pages": p.max_pages,
        } for p in packages], indent=2))
    
    elif action == "add":
        if not name or not url:
            typer.echo("Error: --name and --url are required for add action", err=True)
            raise typer.Exit(code=1)
        
        ensure_app_dirs([path.parent])
        
        # Load existing or create new
        packages = load_external_packages(path) if path.exists() else []
        
        # Check if already exists
        if any(p.name == name for p in packages):
            typer.echo(f"Package '{name}' already exists", err=True)
            raise typer.Exit(code=1)
        
        # Add new package
        packages.append(PackageConfig(name=name, doc_url=url))
        
        # Save back
        data = {
            "packages": [{
                "name": p.name,
                "doc_url": p.doc_url,
                "doc_type": p.doc_type,
                "max_pages": p.max_pages,
                "crawl_delay_seconds": p.crawl_delay_seconds,
            } for p in packages]
        }
        
        if path.suffix.lower() == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            import yaml
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        typer.echo(f"Added package '{name}' to {path}")
    
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        raise typer.Exit(code=1)


# Backward compatibility aliases
@app.command(hidden=True)
def index(
    config: Path | None = typer.Option(None, "--config", "-c"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", "-d"),
    max_pages: int | None = typer.Option(None, "--max-pages", "-m"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """[DEPRECATED] Use 'fetch' instead."""
    typer.echo("Warning: 'index' is deprecated. Use 'fetch' instead.", err=True)
    fetch.callback(
        db=db,
        config=config,
        max_pages=max_pages,
        verbose=verbose,
    )


@app.command(hidden=True)
def sources(
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """[DEPRECATED] Use 'list-sources' instead."""
    typer.echo("Warning: 'sources' is deprecated. Use 'list-sources' instead.", err=True)
    list_sources_cmd.callback(
        db=DEFAULT_DB_PATH,
        format="json",
    )
