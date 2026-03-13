from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

DEFAULT_APP_DIR = Path(os.environ.get("PYDOCS_HOME", Path.home() / ".pydocs_mcp"))
DEFAULT_DB_PATH = Path(os.environ.get("PYDOCS_DB", DEFAULT_APP_DIR / "docs.db"))
DEFAULT_SNAPSHOT_DIR = Path(os.environ.get("PYDOCS_SNAPSHOTS", DEFAULT_APP_DIR / "snapshots"))
DEFAULT_PACKAGES_CONFIG = Path(os.environ.get("PYDOCS_PACKAGES", DEFAULT_APP_DIR / "pydocs-packages.yaml"))


@dataclass
class SourceConfig:
    name: str
    start_urls: list[str]
    allowed_domains: list[str]
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    max_pages: int = 5000
    crawl_delay_seconds: float = 0.2
    user_agent: str = "pydocs-mcp/0.2 (+https://github.com/arsenylosev/pydocs-mcp)"


@dataclass
class PackageConfig:
    """Configuration for an external Python package to download documentation for."""
    name: str
    doc_url: str
    doc_type: str = "auto"  # auto, readthedocs, github, sphinx
    max_pages: int = 1000
    crawl_delay_seconds: float = 0.3


def _read_yaml(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if isinstance(data, dict):
        data = data.get("sources", [])
    if not isinstance(data, list):
        raise ValueError("sources config must be a list or {'sources': [...]} structure")
    return data


def _read_packages_yaml(path: Path) -> list[PackageConfig]:
    """Read external package configuration from YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    
    if isinstance(data, dict):
        packages = data.get("packages", [])
    elif isinstance(data, list):
        packages = data
    else:
        raise ValueError("packages config must be a list or {'packages': [...]} structure")
    
    configs = []
    for item in packages:
        configs.append(PackageConfig(
            name=item["name"],
            doc_url=item["doc_url"],
            doc_type=item.get("doc_type", "auto"),
            max_pages=item.get("max_pages", 1000),
            crawl_delay_seconds=item.get("crawl_delay_seconds", 0.3),
        ))
    return configs


def _read_packages_json(path: Path) -> list[PackageConfig]:
    """Read external package configuration from JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    
    if isinstance(data, dict):
        packages = data.get("packages", [])
    elif isinstance(data, list):
        packages = data
    else:
        raise ValueError("packages config must be a list or {'packages': [...]} structure")
    
    configs = []
    for item in packages:
        configs.append(PackageConfig(
            name=item["name"],
            doc_url=item["doc_url"],
            doc_type=item.get("doc_type", "auto"),
            max_pages=item.get("max_pages", 1000),
            crawl_delay_seconds=item.get("crawl_delay_seconds", 0.3),
        ))
    return configs


def load_sources(config_path: Path | None) -> list[SourceConfig]:
    """Load built-in documentation sources."""
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
                user_agent=str(item.get("user_agent", "pydocs-mcp/0.2 (+https://github.com/arsenylosev/pydocs-mcp)")),
            )
        )
    return sources


def load_external_packages(packages_config_path: Path | None = None) -> list[PackageConfig]:
    """Load external package documentation configurations.
    
    Looks for pydocs-packages.yaml or pydocs-packages.json in the default location
    or at the specified path.
    """
    if packages_config_path is None:
        packages_config_path = DEFAULT_PACKAGES_CONFIG
    
    if not packages_config_path.exists():
        return []
    
    # Determine file type by extension
    if packages_config_path.suffix.lower() == '.json':
        return _read_packages_json(packages_config_path)
    else:
        # Default to YAML
        return _read_packages_yaml(packages_config_path)


def packages_to_sources(packages: list[PackageConfig]) -> list[SourceConfig]:
    """Convert PackageConfig list to SourceConfig list for crawling."""
    sources = []
    for pkg in packages:
        # Parse URL to extract domain
        from urllib.parse import urlparse
        parsed = urlparse(pkg.doc_url)
        domain = parsed.netloc
        
        # Build include pattern based on doc type
        if pkg.doc_type == "readthedocs" or "readthedocs.io" in domain:
            # ReadTheDocs sites have consistent structure
            base_path = parsed.path.rstrip('/')
            include_pattern = f'^https://{domain}{base_path}/'
        elif pkg.doc_type == "github" or "github.com" in domain:
            # GitHub Pages or wiki
            include_pattern = f'^https://{domain}/'
        else:
            # Auto-detect: use the directory of the start URL
            base_path = parsed.path.rstrip('/')
            if base_path:
                include_pattern = f'^https://{domain}{base_path}/'
            else:
                include_pattern = f'^https://{domain}/'
        
        sources.append(SourceConfig(
            name=pkg.name,
            start_urls=[pkg.doc_url],
            allowed_domains=[domain],
            include_patterns=[include_pattern],
            exclude_patterns=['/_sources/', '/search.html', '/genindex.html'],
            max_pages=pkg.max_pages,
            crawl_delay_seconds=pkg.crawl_delay_seconds,
        ))
    return sources


def ensure_app_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def create_sample_packages_config(path: Path) -> None:
    """Create a sample packages configuration file."""
    sample = {
        "packages": [
            {
                "name": "numpy",
                "doc_url": "https://numpy.org/doc/stable/",
                "doc_type": "auto",
                "max_pages": 2000,
                "crawl_delay_seconds": 0.3
            },
            {
                "name": "pandas",
                "doc_url": "https://pandas.pydata.org/docs/",
                "doc_type": "auto",
                "max_pages": 2000,
                "crawl_delay_seconds": 0.3
            },
            {
                "name": "requests",
                "doc_url": "https://requests.readthedocs.io/en/latest/",
                "doc_type": "readthedocs",
                "max_pages": 500,
                "crawl_delay_seconds": 0.3
            }
        ],
        "_comment": "Add your own packages here. doc_type can be: auto, readthedocs, github, sphinx"
    }
    
    if path.suffix.lower() == '.json':
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(sample, f, indent=2)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(sample, f, default_flow_style=False, sort_keys=False)
