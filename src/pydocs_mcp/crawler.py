from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from .config import SourceConfig
from .parser import extract_links, extract_markdown


@dataclass
class CrawledDocument:
    url: str
    source: str
    title: str
    content: str
    fetched_at: str


class Crawler:
    def __init__(self, source: SourceConfig):
        self.source = source
        self._include = [re.compile(p) for p in source.include_patterns]
        self._exclude = [re.compile(p) for p in source.exclude_patterns]

    def crawl(self, *, max_pages: int | None = None) -> Iterable[CrawledDocument]:
        max_pages = max_pages or self.source.max_pages
        seen: set[str] = set()
        queue: deque[str] = deque(self.source.start_urls)

        headers = {"User-Agent": self.source.user_agent}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
            while queue and len(seen) < max_pages:
                url = queue.popleft()
                url = _normalize_url(url)
                if not url or url in seen:
                    continue
                if not _allowed(url, self.source.allowed_domains):
                    continue
                if not _matches(url, self._include, self._exclude):
                    continue

                seen.add(url)
                try:
                    response = client.get(url)
                except httpx.HTTPError:
                    continue
                if response.status_code != 200:
                    continue
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue
                html = response.text
                title, content = extract_markdown(html)
                if not content:
                    continue

                fetched_at = datetime.now(timezone.utc).isoformat()
                yield CrawledDocument(
                    url=url,
                    source=self.source.name,
                    title=title or url,
                    content=content,
                    fetched_at=fetched_at,
                )

                for link in extract_links(html):
                    normalized = _normalize_url(urljoin(url, link))
                    if not normalized or normalized in seen:
                        continue
                    if not _allowed(normalized, self.source.allowed_domains):
                        continue
                    if not _matches(normalized, self._include, self._exclude):
                        continue
                    queue.append(normalized)

                time.sleep(self.source.crawl_delay_seconds)


def _allowed(url: str, domains: list[str]) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def _matches(url: str, include: list[re.Pattern[str]], exclude: list[re.Pattern[str]]) -> bool:
    if include and not any(p.search(url) for p in include):
        return False
    if exclude and any(p.search(url) for p in exclude):
        return False
    return True


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    if parsed.scheme not in {"http", "https"}:
        return ""
    cleaned = parsed._replace(fragment="")
    return urlunparse(cleaned)
