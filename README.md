# Creative AI LLM Wiki Workbench

`Creative AI LLM Wiki Workbench` is a local-first Markdown LLM Wiki for studying **how generative AI changes creative production** across music, images, video, film, advertising, and games.

This is not a generic document dump. It adds a domain-specific analysis layer for creative AI:

- **Creative Impact Lens**: workflow, copyright, creator labor, market/platform, ethics/authenticity
- **Production Pipeline View**: research -> ideation -> generation -> editing -> review -> distribution
- **Risk & Rights Matrix**: industry-by-risk heatmap for copyright, consent, labor, disclosure, and market concerns
- **MCP Tool Access**: the same wiki, graph, lens, pipeline, and risk data can be inspected by an external agent
- **Agent Harness**: operating rules, skill instructions, validation hook, and reviewer subagent spec

The goal is simple: someone should be able to clone this repository, run the included sample wiki immediately, or replace `raw/` with one permitted source file and see their own LLM Wiki in a browser within 30 minutes.

## What This Builds

The workbench turns local source materials into a source-backed Markdown knowledge base:

```text
raw/ source files
  -> scripts/llm_wiki.py compile
  -> wiki/sources/*.md
  -> wiki/concepts/*.md
  -> tools/viewer local GUI
  -> tools/mcp agent-accessible tools
```

The current starter wiki is already usable. It provides concept pages for the Generative AI and Creative Production domain even before the user adds private source material.

## Included Raw Example Materials

This repository intentionally includes example source files in `raw/`. They are starter materials created through deep research for this project domain: **Generative AI and Creative Production**. They let a first-time user clone the repository, run the compiler, and immediately see a working wiki without preparing their own dataset first.

The included raw files are examples, not required system files. Users can:

- add their own permitted `.md`, `.txt`, or `.pdf` source files beside them,
- or replace the contents of `raw/` with their own materials before running `python scripts\llm_wiki.py compile`.


## Repository Contents

```text
.
├─ AGENTS.md                         Agent operating schema
├─ RULES.md                          Project rules and public repo policy
├─ README.md                         Setup and usage guide
├─ requirements.txt                  Python dependencies
├─ raw/                              Included example sources and user source-material drop zone
├─ wiki/                             Markdown LLM Wiki
│  ├─ index.md
│  ├─ overview.md
│  ├─ profile.json                   Personalization and domain taxonomy
│  ├─ concepts/
│  ├─ sources/
│  └─ workflows/
├─ schema/                           Wiki/profile/lens/MCP contracts
├─ scripts/
│  └─ llm_wiki.py                    Compile, query, lint, status
├─ tools/
│  ├─ viewer/app.py                  Local GUI viewer
│  └─ mcp/wiki_server.py             MCP server + CLI fallback tools
├─ harness/
│  ├─ skills/wiki-maintainer/        Agent skill
│  ├─ hooks/validate_wiki.ps1        Validation hook
│  └─ subagents/creative-rights-reviewer.md
├─ demo/                             GUI screenshot location
└─ submission.md                     Submission template
```

## Install

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If you only want to inspect the existing starter wiki, the viewer itself uses only the Python standard library. `pypdf` is needed when compiling PDFs. Markdown and text source files work without PDF extraction. `mcp` is needed when running the MCP server through an MCP client; the CLI fallback works without an MCP client.

## 30-Minute First Run

### 1. Clone and enter the project

```powershell
git clone <repository-url>
cd <repository-folder>
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Check the starter wiki

```powershell
python scripts\llm_wiki.py status
python scripts\llm_wiki.py lint
python tools\viewer\app.py --check
python tools\mcp\wiki_server.py --check
```

### 4. Use or replace the source files in `raw/`

The repository already includes example Markdown source files in `raw/`, so this step is optional if you only want to test the default wiki.

To build your own wiki, add or replace sources with a PDF, Markdown, or text file that you are allowed to process locally.

```powershell
Copy-Item "C:\path\to\creative-ai-report.pdf" raw\
```

If you replace the sample materials, rerun the compiler in the next step.

### 5. Compile the wiki

```powershell
python scripts\llm_wiki.py compile
python scripts\llm_wiki.py lint
```

This creates or refreshes:

- `wiki/sources/*.md`
- `wiki/concepts/*.md`
- `.wiki_cache/text/*.txt`
- `wiki/index.md`
- `wiki/overview.md`
- `wiki/log.md`

### 6. Open the viewer

```powershell
python tools\viewer\app.py --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

The GUI shows the page navigator, Markdown reader, document outline, related pages, searchable catalog, source-concept graph, Creative Impact Lens cards, Production Pipeline, and Risk & Rights Matrix.

## Domain-Specific Feature: Creative Impact Lens

Unlike a generic LLM Wiki, this repository classifies pages through five creative AI analysis lenses.

| Lens | What It Checks |
| --- | --- |
| `workflow` | How AI changes creative production from research to distribution. |
| `copyright` | Training data, outputs, style imitation, licensing, voice, and likeness rights. |
| `creator_labor` | Job roles, creative skills, labor displacement, augmentation, and review work. |
| `market_platform` | Platforms, model providers, studios, tool vendors, subscriptions, and value capture. |
| `ethics_authenticity` | Consent, disclosure, synthetic media, bias, authenticity, and audience trust. |

Concept and source pages can include frontmatter like this:

```yaml
---
title: "Copyright and Licensing"
kind: concept
lenses: "copyright"
pipeline_stages: "generation, distribution"
industries: "music, image, video, film, advertising, game"
risk_level: "high"
---
```

The viewer and MCP tools read this metadata to build the dashboard.

## Visualization Tool

Run:

```powershell
python tools\viewer\app.py --port 8765
```

Main views:

- **Wiki Navigator**: persistent left navigation with page filtering by title, path, kind, and lens
- **Stats**: raw items, wiki pages, concept pages, graph edges, and high-risk page count
- **Document Reader**: rendered Markdown with summary, metadata, lens/risk badges, outline, related pages, and source trail
- **Wiki Catalog**: filterable page catalog by type, Creative Impact Lens, pipeline stage, and risk level
- **Creative Impact Lens**: page counts and high-risk pages by lens
- **Production Pipeline**: pages mapped to research, ideation, generation, editing, review, distribution
- **Risk & Rights Matrix**: quick heatmap across music, image, video, film, advertising, game
- **Search**: keyword retrieval over wiki pages
- **Source-Concept Graph**: Markdown links rendered as a lightweight graph

API endpoints exposed by the viewer:

```text
/api/graph
/api/profile
/api/impact-lenses
/api/pipeline
/api/risk-matrix
/api/catalog
```

## MCP Tools

The MCP server lives in `tools/mcp/wiki_server.py`.

Run a readiness check:

```powershell
python tools\mcp\wiki_server.py --check
```

List tools:

```powershell
python tools\mcp\wiki_server.py --list-tools
```

CLI fallback examples:

```powershell
python tools\mcp\wiki_server.py --call wiki_status
python tools\mcp\wiki_server.py --call search_wiki --query "copyright voice" --limit 3
python tools\mcp\wiki_server.py --call read_wiki_page --path "concepts/copyright-and-licensing.md"
python tools\mcp\wiki_server.py --call get_impact_lenses
python tools\mcp\wiki_server.py --call get_pipeline_map
python tools\mcp\wiki_server.py --call get_risk_matrix
python tools\mcp\wiki_server.py --call list_maintenance_requests
```

Tool list:

| Tool | Behavior |
| --- | --- |
| `wiki_status` | Returns raw/wiki/source/concept counts and graph size. |
| `compile_wiki` | Runs the wiki compiler. |
| `lint_wiki` | Runs structural validation. |
| `search_wiki` | Searches wiki pages and returns scored snippets. |
| `list_wiki_pages` | Lists pages, optionally filtered by kind. |
| `read_wiki_page` | Reads a specific Markdown page. |
| `get_wiki_graph` | Returns source-concept graph data. |
| `get_profile` | Returns `wiki/profile.json`. |
| `create_maintenance_request` | Creates a Markdown task in `wiki/maintenance/inbox/`. |
| `get_impact_lenses` | Returns Creative Impact Lens groups. |
| `get_pipeline_map` | Returns pages grouped by production pipeline stage. |
| `get_risk_matrix` | Returns the Risk & Rights Matrix. |
| `list_maintenance_requests` | Lists maintenance request files. |

To run as an actual MCP server:

```powershell
python tools\mcp\wiki_server.py
```

## Agent Harness

This repo includes a small harness so an LLM agent can maintain the wiki consistently.

- `AGENTS.md`: operating schema for the wiki
- `RULES.md`: public repo policy, source rules, domain rules, safety rules
- `harness/skills/wiki-maintainer/SKILL.md`: maintenance procedure and done criteria
- `harness/hooks/validate_wiki.ps1`: validation hook for lint/viewer/MCP readiness
- `harness/subagents/creative-rights-reviewer.md`: reviewer spec for rights, consent, disclosure, and labor-risk checks

Validation hook:

```powershell
powershell -ExecutionPolicy Bypass -File harness\hooks\validate_wiki.ps1
```

## How To Ask An Agent To Integrate New Material

Example request:

```text
I added a new source file to raw/.
Compile the wiki, inspect generated source and concept pages,
classify the material with Creative Impact Lenses,
check copyright/consent/labor risks,
then update the wiki log.
Do not modify raw files or add API keys.
```

Expected agent flow:

1. Read `AGENTS.md`, `RULES.md`, and `wiki/profile.json`.
2. Run `python scripts\llm_wiki.py compile`.
3. Run `python scripts\llm_wiki.py lint`.
4. Use `python tools\mcp\wiki_server.py --call get_impact_lenses`.
5. Use `python tools\mcp\wiki_server.py --call get_risk_matrix`.
6. Review source and concept pages.
7. Mark uncertain claims as `needs review`.
8. Append important notes to `wiki/log.md`.

## Verification

Run these before publishing:

```powershell
python -m py_compile scripts\llm_wiki.py tools\viewer\app.py tools\mcp\wiki_server.py
python scripts\llm_wiki.py status
python scripts\llm_wiki.py lint
python tools\viewer\app.py --check
python tools\mcp\wiki_server.py --check
python tools\mcp\wiki_server.py --call get_impact_lenses
python tools\mcp\wiki_server.py --call get_pipeline_map
python tools\mcp\wiki_server.py --call get_risk_matrix
```

Then open the GUI:

```powershell
python tools\viewer\app.py --port 8765
```
