# LLM Wiki Operating Schema

This project is a small LLM Wiki workbench for the **Generative AI and Creative Production** domain.

## Purpose

Turn user-provided source materials in `raw/` into a maintained Markdown knowledge base in `wiki/`. The wiki is a compiled layer: it should be easier to read, search, update, visualize, and query than the raw source files.

## Project Layout

- `raw/`: local source files. Do not edit, rename, delete, or publish private source materials during wiki maintenance.
- `.wiki_cache/text/`: extracted text cache generated from source files.
- `wiki/overview.md`: domain-level synthesis.
- `wiki/index.md`: catalog of generated and curated pages.
- `wiki/log.md`: append-only maintenance history.
- `wiki/profile.json`: personalization profile for the viewer and agents.
- `wiki/sources/`: one generated page per raw source.
- `wiki/concepts/`: topic pages synthesized across one or more sources.
- `wiki/workflows/`: maintenance and usage procedures.
- `tools/viewer/`: local GUI viewer.
- `tools/mcp/`: MCP server prototype and CLI fallback tools.
- `schema/`: frontmatter, profile, Creative Impact Lens, and MCP tool contracts.
- `harness/`: skill, hook, and subagent files for repeatable agent operation.
- `scripts/llm_wiki.py`: local compiler and query tool.

## Source Rules

- Raw source files are the source of truth.
- Generated wiki pages must point back to a source page or raw file when making claims.
- Prefer concise synthesis over copied source text.
- When source extraction is noisy, mark the claim as needing review instead of pretending certainty.
- Do not commit private, paid, or copyrighted raw materials to the public repository.

## Domain Analysis Workflow

When maintaining the wiki, use the Creative Impact Lens model:

1. Identify which lens applies: workflow, copyright, creator_labor, market_platform, ethics_authenticity.
2. Map the material to the production pipeline: research, ideation, generation, editing, review, distribution.
3. Identify relevant industries: music, image, video, film, advertising, game.
4. Estimate a conservative risk level: low, medium, high, unknown.
5. If the claim is legal, ethical, or labor-related and has weak evidence, mark it `needs review`.

## Ingest Workflow

1. Add permitted new source files to `raw/`.
2. Run `python scripts/llm_wiki.py compile`.
3. Review changed files in `wiki/`.
4. If a concept page is too shallow, improve it using the source page and raw file.
5. Keep `wiki/log.md` append-only.

## Query Workflow

1. Read `wiki/index.md` first.
2. Open the relevant concept pages.
3. Drill into source pages only when the concept page is not enough.
4. Use raw source files for final verification when precision matters.

## Lint Workflow

Run:

```powershell
python scripts\llm_wiki.py lint
python tools\viewer\app.py --check
python tools\mcp\wiki_server.py --check
python tools\mcp\wiki_server.py --call get_impact_lenses
python tools\mcp\wiki_server.py --call get_pipeline_map
python tools\mcp\wiki_server.py --call get_risk_matrix
```

## Naming

- Use lowercase kebab-case filenames.
- Source pages should preserve useful source identity.
- Concept pages should describe durable ideas, not one-off headlines.

## Human and LLM Roles

- Human: curates sources, asks questions, reviews important claims, controls public sharing.
- LLM: extracts, summarizes, links, updates indexes, flags gaps, and maintains consistency.

## Safety Rules

- Do not store API keys in the repository.
- Do not modify raw source files unless the human explicitly asks.
- Do not make legal or policy claims without source-backed evidence.
- Do not delete legacy materials when archiving would preserve the user's work.
