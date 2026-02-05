from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import SourceConfig
from .crawler import Crawler
from .storage import SQLiteStore


@dataclass
class IndexSummary:
    source: str
    processed: int
    updated: int
    skipped: int


def index_sources(*, db_path: Path, sources: list[SourceConfig], max_pages: int | None = None) -> list[IndexSummary]:
    store = SQLiteStore(db_path)
    store.init_db()
    summaries: list[IndexSummary] = []

    for source in sources:
        crawler = Crawler(source)
        processed = 0
        updated = 0
        skipped = 0
        for document in crawler.crawl(max_pages=max_pages):
            processed += 1
            _, changed = store.upsert_document(
                url=document.url,
                source=document.source,
                title=document.title,
                content=document.content,
                fetched_at=document.fetched_at,
            )
            if changed:
                updated += 1
            else:
                skipped += 1
        summaries.append(
            IndexSummary(
                source=source.name,
                processed=processed,
                updated=updated,
                skipped=skipped,
            )
        )
    return summaries
