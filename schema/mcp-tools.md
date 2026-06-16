# MCP Tool Contract

The MCP server in `tools/mcp/wiki_server.py` exposes safe wiki operations to an external agent.

The same implementation also provides a CLI fallback so the tools can be verified without installing an MCP client.

## Core Tools

| Tool | Purpose |
| --- | --- |
| `wiki_status` | Return raw/wiki/source/concept counts and graph size. |
| `compile_wiki` | Compile raw materials into Markdown wiki pages. |
| `lint_wiki` | Validate required wiki directories and core files. |
| `search_wiki` | Search wiki pages and return scored snippets. |
| `list_wiki_pages` | Return wiki page metadata, optionally filtered by kind. |
| `read_wiki_page` | Read a Markdown wiki page by path. |
| `get_wiki_graph` | Return nodes and edges derived from Markdown links. |
| `get_profile` | Return `wiki/profile.json`. |
| `create_maintenance_request` | Create a Markdown maintenance request in `wiki/maintenance/inbox/`. |

## Domain Tools

| Tool | Purpose |
| --- | --- |
| `get_impact_lenses` | Return page counts and page links grouped by Creative Impact Lens. |
| `get_pipeline_map` | Return pages grouped by creative production stage. |
| `get_risk_matrix` | Return industry-by-risk-lens counts for quick review. |
| `list_maintenance_requests` | Return open maintenance request files. |

## CLI Fallback Examples

```powershell
python tools\mcp\wiki_server.py --check
python tools\mcp\wiki_server.py --list-tools
python tools\mcp\wiki_server.py --call wiki_status
python tools\mcp\wiki_server.py --call search_wiki --query "copyright voice" --limit 3
python tools\mcp\wiki_server.py --call get_risk_matrix
```

