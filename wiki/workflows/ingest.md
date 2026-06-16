---
title: "Ingest Workflow"
kind: workflow
compiled_at: "2026-06-16T17:45:44+09:00"
---

# Ingest Workflow

1. Put permitted `.pdf`, `.md`, or `.txt` source files in `raw/`.
2. Run `python scripts/llm_wiki.py compile`.
3. Review `wiki/sources/` for extraction quality.
4. Review `wiki/concepts/` for missing or weak synthesis.
5. Keep `raw/` immutable and append updates to `wiki/log.md`.
