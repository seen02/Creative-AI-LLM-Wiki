# Wiki Maintainer Skill

Use this skill when maintaining the local LLM Wiki.

## Goal

Keep the Markdown wiki source-backed, searchable, visualizable, and safe for public GitHub distribution.

## Procedure

1. Read `AGENTS.md`, `RULES.md`, and `wiki/profile.json`.
2. Check status:

   ```powershell
   python scripts\llm_wiki.py status
   python scripts\llm_wiki.py lint
   ```

3. If new source files exist in `raw/`, run:

   ```powershell
   python scripts\llm_wiki.py compile
   ```

4. Review generated `wiki/sources/*.md` pages for extraction quality.
5. Review `wiki/concepts/*.md` pages for missing evidence.
6. Make sure concept and source pages include domain metadata:
   - `lenses`
   - `pipeline_stages`
   - `industries`
   - `risk_level`
7. Use the MCP fallback tools to inspect the domain model:

   ```powershell
   python tools\mcp\wiki_server.py --call get_impact_lenses
   python tools\mcp\wiki_server.py --call get_pipeline_map
   python tools\mcp\wiki_server.py --call get_risk_matrix
   ```

8. Run viewer readiness check:

   ```powershell
   python tools\viewer\app.py --check
   ```

9. Append important maintenance notes to `wiki/log.md`.

## Done Criteria

- `python scripts\llm_wiki.py lint` passes.
- `python tools\viewer\app.py --check` passes.
- `python tools\mcp\wiki_server.py --check` passes.
- No private source files are staged for public release.
- Claim-like edits are backed by source pages or marked `needs review`.

