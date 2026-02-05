from __future__ import annotations

from pathlib import Path

from .storage import SQLiteStore


def search_docs(*, db_path: Path, query: str, limit: int = 10, source: str | None = None) -> list[dict]:
    store = SQLiteStore(db_path)
    store.init_db()
    return store.search(query=query, limit=limit, source=source)


def read_doc(*, db_path: Path, doc_id: int | None = None, url: str | None = None):
    store = SQLiteStore(db_path)
    store.init_db()
    return store.get_document(doc_id=doc_id, url=url)
