$ErrorActionPreference = "Stop"

Write-Host "Checking wiki structure..."
python scripts\llm_wiki.py lint

Write-Host "Checking viewer..."
python tools\viewer\app.py --check

Write-Host "Checking MCP prototype..."
python tools\mcp\wiki_server.py --check

Write-Host "Wiki validation completed."

