from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

DEFAULT_APP_DIR = Path(os.environ.get("PYDOCS_HOME", Path.home() / ".pydocs_mcp"))
DEFAULT_DB_PATH = Path(os.environ.get("PYDOCS_DB", DEFAULT_APP_DIR / "docs.db"))
DEFAULT_SNAPSHOT_DIR = Path(os.environ.get("PYDOCS_SNAPSHOTS", DEFAULT_APP_DIR / "snapshots"))


@dataclass
class SourceConfig:
    name: str
    start_urls: list[str]
    allowed_domains: list[str]
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    max_pages: int = 5000
    crawl_delay_seconds: float = 0.2
    user_agent: str = "pydocs-mcp/0.1 (+https://example.local)"


def _read_yaml(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if isinstance(data, dict):
        data = data.get("sources", [])
    if not isinstance(data, list):
        raise ValueError("sources config must be a list or {'sources': [...]} structure")
    return data


def load_sources(config_path: Path | None) -> list[SourceConfig]:
    if config_path is None:
        from importlib import resources

        payloads = yaml.safe_load(
            resources.files("pydocs_mcp.data").joinpath("sources.yaml").read_text(encoding="utf-8")
        )
        if isinstance(payloads, dict):
            payloads = payloads.get("sources", [])
        if not isinstance(payloads, list):
            raise ValueError("sources config must be a list or {'sources': [...]} structure")
    else:
        payloads = _read_yaml(config_path)
    sources: list[SourceConfig] = []
    for item in payloads:
        sources.append(
            SourceConfig(
                name=item["name"],
                start_urls=list(item["start_urls"]),
                allowed_domains=list(item["allowed_domains"]),
                include_patterns=list(item.get("include_patterns", [])),
                exclude_patterns=list(item.get("exclude_patterns", [])),
                max_pages=int(item.get("max_pages", 5000)),
                crawl_delay_seconds=float(item.get("crawl_delay_seconds", 0.2)),
                user_agent=str(item.get("user_agent", "pydocs-mcp/0.1 (+https://example.local)")),
            )
        )
    return sources


def ensure_app_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
