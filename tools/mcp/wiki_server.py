from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
MAINTENANCE_DIR = WIKI_DIR / "maintenance" / "inbox"

IMPACT_LENSES = (
    ("workflow", "Workflow Impact", "How AI changes research, ideation, generation, editing, review, and distribution."),
    ("copyright", "Copyright & Licensing", "Training data, outputs, voice, likeness, style, and commercial rights."),
    ("creator_labor", "Creator Labor", "Creative roles, skills, bargaining power, automation, and augmentation."),
    ("market_platform", "Market & Platform", "Tool vendors, platforms, studios, subscriptions, and value capture."),
    ("ethics_authenticity", "Ethics & Authenticity", "Consent, disclosure, synthetic media, bias, and audience trust."),
)

PIPELINE_STAGES = ("research", "ideation", "generation", "editing", "review", "distribution")
INDUSTRIES = ("music", "image", "video", "film", "advertising", "game")
RISK_LENSES = ("copyright", "consent", "labor", "disclosure", "market")

RISK_KEYWORDS = {
    "copyright": ("copyright", "licensing", "training data", "fair use", "style", "rights", "저작권", "라이선스", "학습 데이터", "공정이용"),
    "consent": ("consent", "voice", "likeness", "performer", "singer", "actor", "동의", "음성", "초상", "퍼블리시티", "보이스"),
    "labor": ("labor", "job", "worker", "role", "automation", "creator", "artist", "노동", "직무", "일자리", "창작자", "자동화"),
    "disclosure": ("disclosure", "label", "authenticity", "synthetic media", "trust", "고지", "표시", "라벨", "진정성", "신뢰", "합성"),
    "market": ("market", "platform", "subscription", "studio", "distribution", "vendor", "시장", "플랫폼", "구독", "스튜디오", "수익", "가치"),
}

RISK_TO_LENSES = {
    "copyright": ("copyright",),
    "consent": ("copyright", "ethics_authenticity"),
    "labor": ("creator_labor",),
    "disclosure": ("ethics_authenticity",),
    "market": ("market_platform",),
}


def risk_priority(score: float) -> str:
    if score >= 6:
        return "focus"
    if score >= 4:
        return "watch"
    if score > 0:
        return "signal"
    return "clear"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, parts[2].lstrip()


def split_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [
        token.strip().lower().replace("-", "_")
        for token in re.split(r"[,;\n]+", value)
        if token.strip()
    ]


def infer_kind(rel: str, metadata: dict[str, str]) -> str:
    if metadata.get("kind"):
        return metadata["kind"]
    if rel.startswith("sources/"):
        return "source"
    if rel.startswith("concepts/"):
        return "concept"
    if rel.startswith("workflows/"):
        return "workflow"
    return "page"


def page_title(rel: str, text: str, metadata: dict[str, str]) -> str:
    if metadata.get("title"):
        return metadata["title"]
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(rel).stem.replace("-", " ").title()


def list_pages_data(kind: str | None = None) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    if not WIKI_DIR.exists():
        return pages
    for path in sorted(WIKI_DIR.rglob("*.md")):
        rel = path.relative_to(WIKI_DIR).as_posix()
        text = read_text(path)
        metadata, body = parse_frontmatter(text)
        page_kind = infer_kind(rel, metadata)
        if kind and page_kind != kind:
            continue
        pages.append(
            {
                "path": f"wiki/{rel}",
                "rel": rel,
                "title": page_title(rel, body, metadata),
                "kind": page_kind,
                "bytes": path.stat().st_size,
                "metadata": metadata,
            }
        )
    return pages


def page_text(page: dict[str, Any]) -> str:
    return read_text(WIKI_DIR / str(page["rel"]))


def page_lenses(page: dict[str, Any]) -> list[str]:
    metadata = page.get("metadata", {})
    explicit = split_tokens(metadata.get("lenses") if isinstance(metadata, dict) else None)
    if explicit:
        return explicit
    lower = page_text(page).lower()
    return [
        lens_id
        for lens_id, _, _ in IMPACT_LENSES
        if lens_id in lower or lens_id.replace("_", " ") in lower
    ]


def page_pipeline_stages(page: dict[str, Any]) -> list[str]:
    metadata = page.get("metadata", {})
    explicit = split_tokens(metadata.get("pipeline_stages") if isinstance(metadata, dict) else None)
    if explicit:
        return explicit
    lower = page_text(page).lower()
    return [stage for stage in PIPELINE_STAGES if stage in lower]


def page_industries(page: dict[str, Any]) -> list[str]:
    metadata = page.get("metadata", {})
    explicit = split_tokens(metadata.get("industries") if isinstance(metadata, dict) else None)
    if explicit:
        return explicit
    lower = page_text(page).lower()
    return [industry for industry in INDUSTRIES if industry in lower]


def page_risk_level(page: dict[str, Any]) -> str:
    metadata = page.get("metadata", {})
    value = ""
    if isinstance(metadata, dict):
        value = str(metadata.get("risk_level", "")).strip().lower()
    return value if value in {"low", "medium", "high", "unknown"} else "unknown"


def resolve_wiki_path(path_value: str) -> Path:
    cleaned = path_value.replace("\\", "/")
    if cleaned.startswith("wiki/"):
        cleaned = cleaned[len("wiki/") :]
    candidate = (WIKI_DIR / cleaned).resolve()
    try:
        candidate.relative_to(WIKI_DIR.resolve())
    except ValueError as exc:
        raise ValueError("Path must stay inside wiki/.") from exc
    if candidate.suffix.lower() != ".md":
        raise ValueError("Only Markdown wiki pages can be read.")
    if not candidate.exists():
        raise FileNotFoundError(f"Wiki page not found: wiki/{cleaned}")
    return candidate


def search_data(query: str, limit: int = 8) -> list[dict[str, Any]]:
    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) > 1]
    if not terms:
        return []
    results: list[dict[str, Any]] = []
    for page in list_pages_data():
        path = WIKI_DIR / page["rel"]
        text = read_text(path)
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)
        phrase = " ".join(terms)
        if len(terms) > 1:
            score += lower.count(phrase) * 25
        if score <= 0:
            continue
        first_idx = min((lower.find(term) for term in terms if lower.find(term) >= 0), default=0)
        start = max(0, first_idx - 120)
        end = min(len(text), first_idx + 260)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet += "..."
        results.append({**page, "score": score, "snippet": snippet})
    results.sort(key=lambda item: int(item["score"]), reverse=True)
    return results[:limit]


def extract_links(rel: str, text: str) -> list[str]:
    links: list[str] = []
    for href in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", text):
        if href.startswith(("http://", "https://")):
            continue
        resolved = (Path(rel).parent / href).as_posix()
        parts: list[str] = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        links.append("/".join(parts))
    return links


def graph_data() -> dict[str, list[dict[str, str]]]:
    pages = list_pages_data()
    page_rels = {page["rel"] for page in pages}
    nodes = [
        {"id": page["rel"], "label": page["title"], "kind": page["kind"]}
        for page in pages
    ]
    edges: list[dict[str, str]] = []
    for page in pages:
        text = read_text(WIKI_DIR / page["rel"])
        for link in extract_links(page["rel"], text):
            if link in page_rels:
                edges.append({"source": page["rel"], "target": link})
    return {"nodes": nodes, "edges": edges}


def impact_lens_data() -> list[dict[str, Any]]:
    pages = [page for page in list_pages_data() if page["kind"] in {"concept", "source"}]
    output: list[dict[str, Any]] = []
    for lens_id, label, description in IMPACT_LENSES:
        linked = [page for page in pages if lens_id in page_lenses(page)]
        output.append(
            {
                "id": lens_id,
                "label": label,
                "description": description,
                "count": len(linked),
                "high_risk": len([page for page in linked if page_risk_level(page) == "high"]),
                "pages": [
                    {
                        "path": page["path"],
                        "rel": page["rel"],
                        "title": page["title"],
                        "kind": page["kind"],
                        "risk_level": page_risk_level(page),
                    }
                    for page in linked
                ],
            }
        )
    return output


def pipeline_map_data() -> list[dict[str, Any]]:
    pages = [page for page in list_pages_data() if page["kind"] in {"concept", "source"}]
    output: list[dict[str, Any]] = []
    for stage in PIPELINE_STAGES:
        linked = [page for page in pages if stage in page_pipeline_stages(page)]
        output.append(
            {
                "stage": stage,
                "count": len(linked),
                "pages": [
                    {
                        "path": page["path"],
                        "rel": page["rel"],
                        "title": page["title"],
                        "kind": page["kind"],
                    }
                    for page in linked
                ],
            }
        )
    return output


def risk_matrix_data() -> list[dict[str, Any]]:
    pages = [page for page in list_pages_data() if page["kind"] == "source"]
    matrix: list[dict[str, Any]] = []
    for industry in INDUSTRIES:
        row: dict[str, Any] = {"industry": industry}
        for risk in RISK_LENSES:
            score = 0.0
            for page in pages:
                page_industry_tokens = page_industries(page)
                if page_industry_tokens and industry not in page_industry_tokens:
                    continue
                text = page_text(page).lower()
                lenses = page_lenses(page)
                is_specific = bool(page_industry_tokens) and len(page_industry_tokens) <= 3
                lens_hit = any(lens in lenses for lens in RISK_TO_LENSES[risk])
                keyword_hit = any(keyword in text for keyword in RISK_KEYWORDS[risk])
                if keyword_hit:
                    score += 2.0 if is_specific else 0.8
                elif lens_hit:
                    score += 1.0 if is_specific else 0.3
            rounded = round(score, 1)
            row[risk] = {"score": rounded, "priority": risk_priority(rounded)}
        matrix.append(row)
    return matrix


def profile_data() -> dict[str, Any]:
    profile_path = WIKI_DIR / "profile.json"
    if profile_path.exists():
        return json.loads(read_text(profile_path))
    return {
        "name": "Personal LLM Wiki",
        "domain": "Markdown Knowledge Base",
        "focus_areas": [],
        "pinned_pages": [],
    }


def raw_source_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    ignored = {"readme.md", ".gitkeep"}
    return [path for path in RAW_DIR.iterdir() if path.is_file() and path.name.lower() not in ignored]


def wiki_status() -> dict[str, Any]:
    pages = list_pages_data()
    graph = graph_data()
    return {
        "root": str(ROOT),
        "raw_items": len(raw_source_files()),
        "wiki_pages": len(pages),
        "source_pages": len([page for page in pages if page["kind"] == "source"]),
        "concept_pages": len([page for page in pages if page["kind"] == "concept"]),
        "workflow_pages": len([page for page in pages if page["kind"] == "workflow"]),
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
    }


def run_script(command: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "llm_wiki.py"), command],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def create_maintenance_request(title: str, body: str) -> dict[str, str]:
    MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    slug = re.sub(r"[^a-z0-9가-힣]+", "-", title.lower()).strip("-") or "request"
    path = MAINTENANCE_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}.md"
    path.write_text(
        f"# {title}\n\n"
        f"- Created at: {stamp}\n"
        "- Status: open\n"
        "- Source: MCP maintenance request\n\n"
        f"{body.strip()}\n",
        encoding="utf-8",
    )
    return {"path": path.relative_to(ROOT).as_posix(), "created_at": stamp}


def list_maintenance_requests() -> list[dict[str, Any]]:
    if not MAINTENANCE_DIR.exists():
        return []
    requests: list[dict[str, Any]] = []
    for path in sorted(MAINTENANCE_DIR.glob("*.md")):
        text = read_text(path)
        first_heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
        requests.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "title": first_heading,
                "bytes": path.stat().st_size,
            }
        )
    return requests


def build_mcp_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            "Missing optional dependency: mcp. Install it with `python -m pip install mcp` "
            "to run the MCP server. Use `--check` or `--call wiki_status` without it."
        ) from exc

    server = FastMCP("personal-llm-wiki")

    @server.tool(name="wiki_status")
    def wiki_status_tool() -> dict[str, Any]:
        """Return raw/wiki counts and graph size."""
        return wiki_status()

    @server.tool(name="compile_wiki")
    def compile_wiki() -> dict[str, Any]:
        """Compile raw materials into Markdown wiki pages."""
        return run_script("compile")

    @server.tool(name="lint_wiki")
    def lint_wiki() -> dict[str, Any]:
        """Validate the required wiki structure."""
        return run_script("lint")

    @server.tool(name="search_wiki")
    def search_wiki(query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Search wiki pages and return scored snippets."""
        return search_data(query, limit)

    @server.tool(name="list_wiki_pages")
    def list_wiki_pages(kind: str | None = None) -> list[dict[str, Any]]:
        """List wiki pages, optionally filtered by kind."""
        return list_pages_data(kind)

    @server.tool(name="read_wiki_page")
    def read_wiki_page(path: str) -> dict[str, str]:
        """Read a Markdown wiki page by path."""
        resolved = resolve_wiki_path(path)
        return {
            "path": resolved.relative_to(ROOT).as_posix(),
            "markdown": read_text(resolved),
        }

    @server.tool(name="get_wiki_graph")
    def get_wiki_graph() -> dict[str, list[dict[str, str]]]:
        """Return nodes and edges derived from Markdown links."""
        return graph_data()

    @server.tool(name="get_profile")
    def get_profile() -> dict[str, Any]:
        """Return the wiki personalization profile."""
        return profile_data()

    @server.tool(name="create_maintenance_request")
    def create_maintenance_request_tool(title: str, body: str) -> dict[str, str]:
        """Create a Markdown maintenance request for later agent work."""
        return create_maintenance_request(title, body)

    @server.tool(name="get_impact_lenses")
    def get_impact_lenses() -> list[dict[str, Any]]:
        """Return page groups for the Creative Impact Lens taxonomy."""
        return impact_lens_data()

    @server.tool(name="get_pipeline_map")
    def get_pipeline_map() -> list[dict[str, Any]]:
        """Return wiki pages grouped by creative production stage."""
        return pipeline_map_data()

    @server.tool(name="get_risk_matrix")
    def get_risk_matrix() -> list[dict[str, Any]]:
        """Return industry-by-risk-lens review priority scores."""
        return risk_matrix_data()

    @server.tool(name="list_maintenance_requests")
    def list_maintenance_requests_tool() -> list[dict[str, Any]]:
        """List maintenance request Markdown files."""
        return list_maintenance_requests()

    return server


def call_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "wiki_status":
        return wiki_status()
    if name == "list_wiki_pages":
        return list_pages_data(args.get("kind"))
    if name == "read_wiki_page":
        return {"markdown": read_text(resolve_wiki_path(str(args["path"])))}
    if name == "search_wiki":
        return search_data(str(args["query"]), int(args.get("limit", 8)))
    if name == "get_wiki_graph":
        return graph_data()
    if name == "get_profile":
        return profile_data()
    if name == "create_maintenance_request":
        return create_maintenance_request(str(args["title"]), str(args["body"]))
    if name == "get_impact_lenses":
        return impact_lens_data()
    if name == "get_pipeline_map":
        return pipeline_map_data()
    if name == "get_risk_matrix":
        return risk_matrix_data()
    if name == "list_maintenance_requests":
        return list_maintenance_requests()
    if name == "lint_wiki":
        return run_script("lint")
    if name == "compile_wiki":
        return run_script("compile")
    raise SystemExit(f"Unknown tool: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP server for the local LLM Wiki.")
    parser.add_argument("--check", action="store_true", help="Print server readiness and exit.")
    parser.add_argument("--list-tools", action="store_true", help="List available tool names and exit.")
    parser.add_argument("--call", help="Call one tool in CLI fallback mode.")
    parser.add_argument("--args", default="{}", help="JSON arguments for --call.")
    parser.add_argument("--query", help="Convenience argument for search_wiki.")
    parser.add_argument("--limit", type=int, help="Convenience argument for search_wiki.")
    parser.add_argument("--path", help="Convenience argument for read_wiki_page.")
    parser.add_argument("--kind", help="Convenience argument for list_wiki_pages.")
    parser.add_argument("--title", help="Convenience argument for create_maintenance_request.")
    parser.add_argument("--body", help="Convenience argument for create_maintenance_request.")
    args = parser.parse_args()

    tools = [
        "wiki_status",
        "compile_wiki",
        "lint_wiki",
        "search_wiki",
        "list_wiki_pages",
        "read_wiki_page",
        "get_wiki_graph",
        "get_profile",
        "create_maintenance_request",
        "get_impact_lenses",
        "get_pipeline_map",
        "get_risk_matrix",
        "list_maintenance_requests",
    ]
    if args.check:
        print(json.dumps({"status": "ready", "tools": tools, **wiki_status()}, ensure_ascii=False, indent=2))
        return 0
    if args.list_tools:
        print(json.dumps(tools, indent=2))
        return 0
    if args.call:
        try:
            payload = json.loads(args.args)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                "Could not parse --args as JSON. On Windows, prefer convenience flags "
                "such as `--query`, `--path`, `--kind`, `--title`, and `--body`."
            ) from exc
        if args.query is not None:
            payload["query"] = args.query
        if args.limit is not None:
            payload["limit"] = args.limit
        if args.path is not None:
            payload["path"] = args.path
        if args.kind is not None:
            payload["kind"] = args.kind
        if args.title is not None:
            payload["title"] = args.title
        if args.body is not None:
            payload["body"] = args.body
        print(json.dumps(call_tool(args.call, payload), ensure_ascii=False, indent=2))
        return 0

    server = build_mcp_server()
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
