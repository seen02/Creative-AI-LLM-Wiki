---
title: "Query Workflow"
kind: workflow
compiled_at: "2026-06-16T17:45:44+09:00"
---

# Query Workflow

1. Start from `wiki/index.md`.
2. Read `wiki/overview.md` for the domain-level map.
3. Open the concept page that matches the question.
4. Drill into source pages when you need evidence.
5. Verify exact claims against the original source file in `raw/`.

Local keyword search:

```powershell
python scripts/llm_wiki.py query "copyright voice"
```
