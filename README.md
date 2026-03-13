# pydocs-mcp

Offline Python documentation as an MCP server. This mirrors the architecture from the [Cupertino repository](https://github.com/mihaelamj/cupertino) but targets Python official documentation (docs.python.org).

## What is pydocs-mcp?

A local, structured, AI-ready documentation system for Python. It:

- **Downloads** official Python documentation from docs.python.org
- **Indexes** everything into a fast, searchable SQLite FTS5 database
- **Serves** documentation to AI agents via the Model Context Protocol
- **Provides** offline access to Python language and standard library docs

### Why Build This?

- **No more hallucinations**: AI agents get accurate, up-to-date Python documentation
- **Offline development**: Work with full documentation without internet access
- **Deterministic search**: Same query always returns same results
- **Local control**: Own your documentation, inspect the database, script workflows
- **AI-first design**: Built specifically for AI agent integration via MCP

## Quick Start

### Installation

```bash
git clone https://github.com/arsenylosev/pydocs-mcp.git
cd pydocs-mcp
uv sync
```

### Setup

One-command setup downloads and indexes Python documentation:

```bash
uv run pydocs-mcp setup
```

Or step by step:

```bash
# Download documentation
uv run pydocs-mcp fetch

# Verify index
uv run pydocs-mcp stats
```

### Use with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pydocs": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pydocs-mcp", "pydocs-mcp", "serve"]
    }
  }
}
```

### Use with Claude Code

```bash
claude mcp add pydocs --scope user -- uv run --directory /path/to/pydocs-mcp pydocs-mcp serve
```

### Use with VS Code (GitHub Copilot)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "pydocs": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pydocs-mcp", "pydocs-mcp", "serve"]
    }
  }
}
```

## Commands

| Command | Description |
|---------|-------------|
| `setup` | Quick setup: download docs and build index |
| `fetch` | Download documentation from configured sources |
| `save` | Build or refresh the search index |
| `serve` | Start MCP server over stdio |
| `search` | Search the documentation index |
| `read` | Read a full document by ID or URL |
| `list-sources` | List configured sources |
| `stats` | Show database statistics |
| `packages` | Manage external package documentation |

## External Packages

By default, pydocs-mcp only downloads official Python documentation. You can add external packages (NumPy, Pandas, etc.) via a configuration file.

### Initialize packages config

```bash
uv run pydocs-mcp packages init
```

This creates `~/.pydocs_mcp/pydocs-packages.yaml` with sample packages.

### Example packages config

```yaml
packages:
  - name: numpy
    doc_url: https://numpy.org/doc/stable/
    doc_type: auto
    max_pages: 2000
    crawl_delay_seconds: 0.3

  - name: pandas
    doc_url: https://pandas.pydata.org/docs/
    doc_type: auto
    max_pages: 2000

  - name: requests
    doc_url: https://requests.readthedocs.io/en/latest/
    doc_type: readthedocs
    max_pages: 500
```

### Fetch external packages

```bash
# Fetch all configured sources + external packages
uv run pydocs-mcp fetch

# Fetch only a specific package
uv run pydocs-mcp fetch --source numpy
```

### Add a package from CLI

```bash
uv run pydocs-mcp packages add --name flask --url https://flask.palletsprojects.com/
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYDOCS_HOME` | `~/.pydocs_mcp` | Base directory for data |
| `PYDOCS_DB` | `~/.pydocs_mcp/docs.db` | SQLite database path |
| `PYDOCS_PACKAGES` | `~/.pydocs_mcp/pydocs-packages.yaml` | External packages config |

### Custom Sources

For advanced use cases, you can provide a custom sources configuration:

```bash
uv run pydocs-mcp fetch --config /path/to/custom-sources.yaml
```

## Search Examples

```bash
# Search for list comprehensions
uv run pydocs-mcp search "list comprehension"

# Search with text output
uv run pydocs-mcp search "context manager" --format text

# Search within specific source
uv run pydocs-mcp search "asyncio" --source python-library

# Read a specific document
uv run pydocs-mcp read --url "https://docs.python.org/3/library/asyncio.html"
```

## Architecture

This project follows the Cupertino architecture pattern:

```
Foundation Layer:
  ├─ config.py          # Configuration management
  ├─ log.py             # Logging infrastructure
  └─ parser.py          # HTML to Markdown conversion

Infrastructure Layer:
  ├─ crawler.py         # Web crawling
  ├─ storage.py         # SQLite FTS5 storage
  └─ indexer.py         # Document indexing

Application Layer:
  ├─ search.py          # Search API
  └─ mcp_server.py      # MCP server implementation

Interface Layer:
  └─ cli.py             # CLI commands
```

## Default Sources

Built-in sources (official Python documentation only):

- `python` - Main Python 3 documentation
- `python-tutorial` - Python tutorial
- `python-library` - Python standard library
- `python-reference` - Python language reference
- `python-howto` - Python HOWTOs

## MCP Tools

- `search_docs(query, limit=10, source=None)` - Full-text search
- `read_doc(doc_id=None, url=None)` - Read document by ID or URL
- `list_sources()` - List available sources
- `get_stats()` - Get database statistics

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run ruff format .
uv run ruff check . --fix
```

## Differences from Original pydocs-mcp

The original project downloaded many ML libraries (NumPy, Pandas, PyTorch, etc.) by default. This version:

1. **Focuses on Python official docs** - Only docs.python.org by default
2. **Optional external packages** - ML libraries can be added via config
3. **Cupertino-style CLI** - Commands organized as setup, fetch, save, serve
4. **Better source management** - Filter by source, list sources, etc.

## License

MIT License

## Acknowledgments

- Inspired by [Cupertino](https://github.com/mihaelamj/cupertino) for Apple documentation
- Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
