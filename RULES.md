# Project Rules

These rules define how humans, agents, and tools should maintain this LLM Wiki workbench.

## Public Repository Rules

- The repository must be public for assignment submission.
- Do not commit private PDFs, paid articles, course slides, unpublished scripts, audio, video, or copyrighted images.
- Keep `raw/` in the repository, but publish only `raw/README.md` and `raw/.gitkeep`.
- Keep local legacy material under `archive/`; it is ignored by Git.
- Do not commit API keys, tokens, `.env` files, or model provider credentials.

## Source Rules

- `raw/` files are source of truth.
- Do not edit or delete source files unless the user explicitly asks.
- Generated wiki pages should cite source pages or raw paths for claim-like statements.
- If extracted text is noisy, mark the claim as `needs review`.

## Domain Rules

This wiki is specialized for **Generative AI and Creative Production**.

Every concept or source page should be classified with:

- `lenses`: workflow, copyright, creator_labor, market_platform, ethics_authenticity
- `pipeline_stages`: research, ideation, generation, editing, review, distribution
- `industries`: music, image, video, film, advertising, game
- `risk_level`: low, medium, high, unknown

## Agent Rules

- Start from `wiki/index.md`.
- Read `wiki/profile.json` before deciding maintenance priority.
- Use `python scripts/llm_wiki.py lint` after structural changes.
- Use `python tools/viewer/app.py --check` after viewer-related changes.
- Use `python tools/mcp/wiki_server.py --check` after MCP tool changes.
- Append important maintenance events to `wiki/log.md`.
- Prefer small, source-backed edits over broad unsourced rewriting.

## Safety Rules

- Do not make legal conclusions as final advice.
- Use phrases such as "the source suggests" or "needs legal review" when discussing law or policy.
- Do not embed a chatbot API call or API key in the application.
- If an external LLM is used, call it outside this repository through a user-controlled process or MCP client.

