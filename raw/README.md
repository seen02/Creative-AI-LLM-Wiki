# Raw Source Materials

This directory contains the source materials used by the compiler before it generates pages in `wiki/`.

The repository includes example Markdown source files in this folder. They were created through deep research for the default domain, **Generative AI and Creative Production**, so someone who clones the repository can run the project immediately without preparing a separate dataset.

These files are replaceable examples. To build your own LLM Wiki, keep them, add your own files beside them, or replace them with materials you are allowed to process and share.

Supported source types:

- `.pdf`
- `.md`
- `.txt`

Recommended public-repo policy:

- Commit only raw materials that you are allowed to redistribute.
- Do not commit private PDFs, paid articles, confidential notes, course slides, scripts, audio, video, images, or API keys.
- If you use this repository for a private knowledge base, replace the sample files locally and keep private materials out of the public repo.

Example:

```powershell
Copy-Item "C:\Users\me\Downloads\creative-ai-report.pdf" raw\
python scripts\llm_wiki.py compile
```
