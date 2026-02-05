from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class DocumentRecord:
    id: int
    url: str
    source: str
    title: str
    content: str
    fetched_at: str


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title, content, source, url,
                    content='documents',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, title, content, source, url)
                    VALUES (new.id, new.title, new.content, new.source, new.url);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, content, source, url)
                    VALUES('delete', old.id, old.title, old.content, old.source, old.url);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, content, source, url)
                    VALUES('delete', old.id, old.title, old.content, old.source, old.url);
                    INSERT INTO documents_fts(rowid, title, content, source, url)
                    VALUES (new.id, new.title, new.content, new.source, new.url);
                END;
                """
            )

    def upsert_document(
        self,
        *,
        url: str,
        source: str,
        title: str,
        content: str,
        fetched_at: str,
    ) -> tuple[int, bool]:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id, content_hash FROM documents WHERE url = ?",
                (url,),
            ).fetchone()
            if existing and existing["content_hash"] == content_hash:
                return int(existing["id"]), False
            if existing:
                conn.execute(
                    """
                    UPDATE documents
                    SET source = ?, title = ?, content = ?, content_hash = ?, fetched_at = ?
                    WHERE url = ?
                    """,
                    (source, title, content, content_hash, fetched_at, url),
                )
                return int(existing["id"]), True
            cursor = conn.execute(
                """
                INSERT INTO documents (url, source, title, content, content_hash, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (url, source, title, content, content_hash, fetched_at),
            )
            return int(cursor.lastrowid), True

    def get_document(self, *, doc_id: int | None = None, url: str | None = None) -> DocumentRecord | None:
        if doc_id is None and url is None:
            raise ValueError("doc_id or url is required")
        with self.connect() as conn:
            if doc_id is not None:
                row = conn.execute(
                    "SELECT id, url, source, title, content, fetched_at FROM documents WHERE id = ?",
                    (doc_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, url, source, title, content, fetched_at FROM documents WHERE url = ?",
                    (url,),
                ).fetchone()
        if row is None:
            return None
        return DocumentRecord(
            id=int(row["id"]),
            url=str(row["url"]),
            source=str(row["source"]),
            title=str(row["title"]),
            content=str(row["content"]),
            fetched_at=str(row["fetched_at"]),
        )

    def search(self, *, query: str, limit: int = 10, source: str | None = None) -> list[dict[str, Any]]:
        where_clause = "documents_fts MATCH ?"
        params: list[Any] = [query]
        if source:
            where_clause += " AND documents.source = ?"
            params.append(source)
        params.append(limit)
        sql = f"""
            SELECT documents.id, documents.title, documents.url, documents.source,
                   bm25(documents_fts) AS score,
                   snippet(documents_fts, 1, '[', ']', '...', 12) AS snippet
            FROM documents_fts
            JOIN documents ON documents_fts.rowid = documents.id
            WHERE {where_clause}
            ORDER BY score
            LIMIT ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "id": int(row["id"]),
                    "title": str(row["title"]),
                    "url": str(row["url"]),
                    "source": str(row["source"]),
                    "score": float(row["score"]),
                    "snippet": str(row["snippet"]) if row["snippet"] is not None else "",
                }
            )
        return results

    def list_sources(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) AS count FROM documents GROUP BY source ORDER BY source"
            ).fetchall()
        return [{"source": row["source"], "count": int(row["count"])} for row in rows]

    def stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return {"documents": int(row["count"]) if row else 0}

    def iter_urls(self) -> Iterable[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT url FROM documents").fetchall()
        for row in rows:
            yield str(row["url"])
