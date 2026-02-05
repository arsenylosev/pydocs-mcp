from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .storage import SQLiteStore


def create_server(db_path: Path) -> FastMCP:
    store = SQLiteStore(db_path)
    store.init_db()

    mcp = FastMCP("Python Docs MCP")

    @mcp.tool()
    def search_docs(query: str, limit: int = 10, source: str | None = None) -> list[dict]:
        """Search the documentation index with FTS5."""
        return store.search(query=query, limit=limit, source=source)

    @mcp.tool()
    def read_doc(doc_id: int | None = None, url: str | None = None) -> dict:
        """Return a full document by id or url."""
        if doc_id is None and url is None:
            return {"error": "doc_id or url is required"}
        record = store.get_document(doc_id=doc_id, url=url)
        if record is None:
            return {"error": "Document not found"}
        return {
            "id": record.id,
            "url": record.url,
            "source": record.source,
            "title": record.title,
            "content": record.content,
            "fetched_at": record.fetched_at,
        }

    @mcp.tool()
    def list_sources() -> list[dict]:
        """List known sources and document counts."""
        return store.list_sources()

    @mcp.tool()
    def get_stats() -> dict:
        """Return database statistics."""
        return store.stats()

    return mcp
