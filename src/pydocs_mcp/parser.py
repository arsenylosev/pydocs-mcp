from __future__ import annotations

import re
from typing import Iterable

from markdownify import markdownify as md
from selectolax.parser import HTMLParser


MAIN_SELECTORS: tuple[str, ...] = (
    "main",
    "article",
    "#main-content",
    "#content",
    ".document",
    ".content",
    ".main-content",
)


def extract_markdown(html: str) -> tuple[str, str]:
    tree = HTMLParser(html)
    if tree.body is None:
        return "", ""

    for node in tree.css("script, style, noscript"):
        node.decompose()

    title_node = tree.css_first("title")
    title = title_node.text().strip() if title_node else ""

    content_html = None
    for selector in MAIN_SELECTORS:
        node = tree.css_first(selector)
        if node is not None:
            content_html = node.html
            break
    if content_html is None:
        content_html = tree.body.html

    markdown = md(content_html or "", heading_style="ATX")
    text = _normalize(markdown)
    return title, text


def extract_links(html: str) -> Iterable[str]:
    tree = HTMLParser(html)
    if tree.body is None:
        return []
    for node in tree.css("a[href]"):
        href = node.attributes.get("href")
        if href:
            yield href


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
