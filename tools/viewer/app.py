from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse


ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"
STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class WikiPage:
    rel: str
    path: Path
    title: str
    kind: str
    text: str
    metadata: dict[str, str]


IMPACT_LENSES = (
    ("workflow", "Workflow Impact", "Research, ideation, generation, editing, review, and distribution changes."),
    ("copyright", "Copyright & Licensing", "Training data, outputs, voice, likeness, style, and commercial rights."),
    ("creator_labor", "Creator Labor", "Roles, skills, bargaining power, automation, and augmentation."),
    ("market_platform", "Market & Platform", "Tool vendors, platforms, studios, subscriptions, and value capture."),
    ("ethics_authenticity", "Ethics & Authenticity", "Consent, disclosure, synthetic media, bias, and audience trust."),
)

PIPELINE_STAGES = ("research", "ideation", "generation", "editing", "review", "distribution")
INDUSTRIES = ("music", "image", "video", "film", "advertising", "game")
RISK_LENSES = ("copyright", "consent", "labor", "disclosure", "market")
PAGE_KIND_ORDER = ("overview", "index", "concept", "source", "workflow", "page")
PAGE_KIND_LABELS = {
    "overview": "Overview",
    "index": "Index",
    "concept": "Concept",
    "source": "Source",
    "workflow": "Workflow",
    "page": "Page",
}

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

CONCEPT_GRAPH_ORDER = (
    "creative-ai-workflows",
    "copyright-and-licensing",
    "music-generation-and-voice",
    "image-video-and-film-production",
    "creator-labor-and-roles",
    "ethics-and-authenticity",
    "market-structure-and-platforms",
)

SOURCE_CONCEPT_HINTS = {
    "01-": ("creative-ai-workflows", "market-structure-and-platforms"),
    "02-": ("music-generation-and-voice", "copyright-and-licensing"),
    "03-": ("image-video-and-film-production", "creator-labor-and-roles"),
    "04-": ("creative-ai-workflows", "ethics-and-authenticity"),
    "05-": ("image-video-and-film-production", "creator-labor-and-roles"),
    "06-": ("copyright-and-licensing", "market-structure-and-platforms"),
    "07-": ("creator-labor-and-roles", "market-structure-and-platforms"),
    "08-": ("ethics-and-authenticity", "copyright-and-licensing"),
}

CONCEPT_WORKFLOW_HINTS = {
    "creative-ai-workflows": ("workflows/ingest.md", "workflows/lint.md"),
    "copyright-and-licensing": ("workflows/lint.md", "workflows/query.md"),
    "music-generation-and-voice": ("workflows/ingest.md", "workflows/lint.md"),
    "image-video-and-film-production": ("workflows/ingest.md", "workflows/lint.md"),
    "creator-labor-and-roles": ("workflows/query.md",),
    "ethics-and-authenticity": ("workflows/lint.md", "workflows/query.md"),
    "market-structure-and-platforms": ("workflows/query.md",),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data, parts[2].lstrip()


def split_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.strip().strip("[]")
    tokens: list[str] = []
    for token in re.split(r"[,;\n]+", cleaned):
        item = token.strip().strip("\"'").lower().replace("-", "_")
        if item:
            tokens.append(item)
    return tokens


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_markdown(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_>#-]+", " ", value)
    return compact(value)


def slugify_id(value: str) -> str:
    value = strip_markdown(value).lower()
    value = re.sub(r"[^a-z0-9가-힣]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"


def page_lenses(page: WikiPage) -> list[str]:
    explicit = split_tokens(page.metadata.get("lenses"))
    if explicit:
        return explicit
    lower = page.text.lower()
    matches = []
    for lens_id, _, _ in IMPACT_LENSES:
        if lens_id.replace("_", " ") in lower or lens_id in lower:
            matches.append(lens_id)
    return matches


def page_pipeline_stages(page: WikiPage) -> list[str]:
    explicit = split_tokens(page.metadata.get("pipeline_stages"))
    if explicit:
        return explicit
    lower = page.text.lower()
    return [stage for stage in PIPELINE_STAGES if stage in lower]


def page_industries(page: WikiPage) -> list[str]:
    explicit = split_tokens(page.metadata.get("industries"))
    if explicit:
        return explicit
    lower = page.text.lower()
    return [industry for industry in INDUSTRIES if industry in lower]


def page_risk_level(page: WikiPage) -> str:
    value = (page.metadata.get("risk_level") or "").strip().lower()
    if value in {"low", "medium", "high", "unknown"}:
        return value
    if page_lenses(page):
        return "medium"
    return "unknown"


def infer_kind(rel: str, frontmatter: dict[str, str]) -> str:
    if frontmatter.get("kind"):
        return frontmatter["kind"]
    if rel == "overview.md":
        return "overview"
    if rel == "index.md":
        return "index"
    if rel.startswith("sources/"):
        return "source"
    if rel.startswith("concepts/"):
        return "concept"
    if rel.startswith("workflows/"):
        return "workflow"
    return "page"


def title_from_page(rel: str, text: str, frontmatter: dict[str, str]) -> str:
    if frontmatter.get("title"):
        return frontmatter["title"]
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(rel).stem.replace("-", " ").title()


def safe_page_rel(raw: str | None) -> str:
    if not raw:
        return "overview.md"
    decoded = raw.replace("\\", "/").lstrip("/")
    path = Path(decoded)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".md":
        return "overview.md"
    candidate = (WIKI_DIR / path).resolve()
    try:
        candidate.relative_to(WIKI_DIR.resolve())
    except ValueError:
        return "overview.md"
    if not candidate.exists():
        return "overview.md"
    return path.as_posix()


def iter_pages() -> list[WikiPage]:
    pages: list[WikiPage] = []
    if not WIKI_DIR.exists():
        return pages
    for path in sorted(WIKI_DIR.rglob("*.md")):
        rel = path.relative_to(WIKI_DIR).as_posix()
        text = read_text(path)
        frontmatter, body = parse_frontmatter(text)
        pages.append(
            WikiPage(
                rel=rel,
                path=path,
                title=title_from_page(rel, body, frontmatter),
                kind=infer_kind(rel, frontmatter),
                text=text,
                metadata=frontmatter,
            )
        )
    return sorted(pages, key=lambda page: (PAGE_KIND_ORDER.index(page.kind) if page.kind in PAGE_KIND_ORDER else 99, page.title))


def load_profile() -> dict[str, object]:
    profile_path = WIKI_DIR / "profile.json"
    if profile_path.exists():
        try:
            return json.loads(read_text(profile_path))
        except json.JSONDecodeError:
            pass
    return {
        "name": "Personal LLM Wiki",
        "domain": "Markdown Knowledge Base",
        "persona": "student-researcher",
        "description": "A local source-backed Markdown wiki.",
        "focus_areas": ["source-backed notes", "concept pages", "agent maintenance"],
        "pinned_pages": ["wiki/overview.md"],
    }


def raw_source_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    ignored = {"readme.md", ".gitkeep"}
    return [path for path in RAW_DIR.iterdir() if path.is_file() and path.name.lower() not in ignored]


def page_counts(pages: list[WikiPage]) -> dict[str, int]:
    counts = {
        "raw": len(raw_source_files()),
        "pages": len(pages),
        "sources": 0,
        "concepts": 0,
        "workflows": 0,
        "high_risk": 0,
    }
    for page in pages:
        if page.kind == "source":
            counts["sources"] += 1
        elif page.kind == "concept":
            counts["concepts"] += 1
        elif page.kind == "workflow":
            counts["workflows"] += 1
        if page_risk_level(page) == "high":
            counts["high_risk"] += 1
    return counts


def extract_links(page: WikiPage) -> list[str]:
    links: list[str] = []
    for href in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", page.text):
        if href.startswith(("http://", "https://")):
            continue
        target = href.split("#", 1)[0]
        resolved = (Path(page.rel).parent / target).as_posix()
        parts: list[str] = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        links.append("/".join(parts))
    return links


def build_graph(pages: list[WikiPage]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    page_by_rel = {page.rel: page for page in pages}
    nodes = [
        {"id": page.rel, "label": page.title, "kind": page.kind}
        for page in pages
        if page.kind in {"source", "concept", "workflow", "overview", "index", "page"}
    ]
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for page in pages:
        if page.rel not in node_ids:
            continue
        for link in extract_links(page):
            edge = (page.rel, link)
            if link in page_by_rel and link in node_ids and edge not in seen_edges:
                edges.append({"source": page.rel, "target": link})
                seen_edges.add(edge)
    return nodes, edges


def page_url(rel: str) -> str:
    return f"/page?path={quote(rel)}"


def url_with(**params: str) -> str:
    clean = {key: value for key, value in params.items() if value}
    return "/?" + urlencode(clean) if clean else "/"


def escape_inline(text: str, current_rel: str) -> str:
    escaped = html.escape(text)

    def link_repl(match: re.Match[str]) -> str:
        label = match.group(1)
        href = html.unescape(match.group(2))
        if href.startswith(("http://", "https://")):
            safe_href = html.escape(href, quote=True)
        elif ".md" in href:
            target = href.split("#", 1)[0]
            resolved = (Path(current_rel).parent / target).as_posix()
            resolved = re.sub(r"(^|/)\./", "/", resolved).lstrip("/")
            parts: list[str] = []
            for part in resolved.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part and part != ".":
                    parts.append(part)
            safe_href = page_url("/".join(parts))
        else:
            safe_href = html.escape(href, quote=True)
        return f'<a href="{safe_href}">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def section_default_open(title: str) -> bool:
    normalized = strip_markdown(title).lower()
    always_open = {
        "summary",
        "key claims",
        "creative impact mapping",
        "first signal",
        "domain-level synthesis",
        "special analysis layer",
    }
    return normalized in always_open


def render_markdown(markdown: str, current_rel: str) -> str:
    _, body = parse_frontmatter(markdown)
    blocks: list[str] = []
    in_code = False
    code_lines: list[str] = []
    unordered_items: list[str] = []
    ordered_items: list[str] = []
    used_ids: dict[str, int] = {}
    section_open = False

    def heading_id(title: str) -> str:
        base = slugify_id(title)
        count = used_ids.get(base, 0)
        used_ids[base] = count + 1
        return base if count == 0 else f"{base}-{count + 1}"

    def flush_lists() -> None:
        if unordered_items:
            blocks.append("<ul>" + "".join(unordered_items) + "</ul>")
            unordered_items.clear()
        if ordered_items:
            blocks.append("<ol>" + "".join(ordered_items) + "</ol>")
            ordered_items.clear()

    def close_section() -> None:
        nonlocal section_open
        if section_open:
            flush_lists()
            blocks.append("</div></details>")
            section_open = False

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_lists()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_lists()
            continue
        if line.startswith("# "):
            flush_lists()
            close_section()
            title = line[2:].strip()
            blocks.append(f'<h1 id="{heading_id(title)}">{escape_inline(title, current_rel)}</h1>')
        elif line.startswith("## "):
            flush_lists()
            close_section()
            title = line[3:].strip()
            section_id = heading_id(title)
            open_attr = " open" if section_default_open(title) else ""
            blocks.append(
                f'<details class="doc-section"{open_attr} id="{section_id}">'
                f'<summary><span>{escape_inline(title, current_rel)}</span></summary>'
                '<div class="section-content">'
            )
            section_open = True
        elif line.startswith("### "):
            flush_lists()
            title = line[4:].strip()
            blocks.append(f'<h3 id="{heading_id(title)}">{escape_inline(title, current_rel)}</h3>')
        elif line.startswith("- "):
            ordered_items.clear()
            unordered_items.append(f"<li>{escape_inline(line[2:].strip(), current_rel)}</li>")
        elif re.match(r"^\d+\.\s+", line):
            unordered_items.clear()
            item = re.sub(r"^\d+\.\s+", "", line)
            ordered_items.append(f"<li>{escape_inline(item, current_rel)}</li>")
        elif line.startswith("> "):
            flush_lists()
            blocks.append(f"<blockquote>{escape_inline(line[2:].strip(), current_rel)}</blockquote>")
        else:
            flush_lists()
            blocks.append(f"<p>{escape_inline(line, current_rel)}</p>")
    flush_lists()
    close_section()
    if in_code:
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(blocks)


def search_pages(query: str, pages: list[WikiPage], limit: int = 12) -> list[tuple[int, WikiPage, str]]:
    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) > 1]
    if not terms:
        return []
    results: list[tuple[int, WikiPage, str]] = []
    for page in pages:
        lower = page.text.lower()
        score = sum(lower.count(term) for term in terms)
        phrase = " ".join(terms)
        if len(terms) > 1:
            score += lower.count(phrase) * 25
        if score <= 0:
            continue
        first_idx = min((lower.find(term) for term in terms if lower.find(term) >= 0), default=0)
        start = max(0, first_idx - 120)
        end = min(len(page.text), first_idx + 280)
        snippet = compact(page.text[start:end])
        if start > 0:
            snippet = "..." + snippet
        if end < len(page.text):
            snippet += "..."
        results.append((score, page, strip_markdown(snippet)))
    results.sort(key=lambda item: item[0], reverse=True)
    return results[:limit]


def section_text(page: WikiPage, heading: str) -> str:
    _, body = parse_frontmatter(page.text)
    lines = body.splitlines()
    start = -1
    for index, line in enumerate(lines):
        if line.strip().lower() == f"## {heading}".lower():
            start = index + 1
            break
    if start < 0:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def page_summary(page: WikiPage, limit: int = 340) -> str:
    for heading in ("Summary", "First Signal", "Domain-Level Synthesis", "Why It Matters"):
        text = section_text(page, heading)
        if text:
            summary = strip_markdown(text)
            return summary[:limit].rstrip() + ("..." if len(summary) > limit else "")
    _, body = parse_frontmatter(page.text)
    summary = strip_markdown(body)
    return summary[:limit].rstrip() + ("..." if len(summary) > limit else "")


def reading_time(page: WikiPage) -> int:
    words = len(re.findall(r"\S+", strip_markdown(page.text)))
    return max(1, math.ceil(words / 220))


def extract_headings(page: WikiPage) -> list[tuple[int, str, str]]:
    _, body = parse_frontmatter(page.text)
    headings: list[tuple[int, str, str]] = []
    used: dict[str, int] = {}
    for line in body.splitlines():
        match = re.match(r"^(#{2,3})\s+(.+)$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = strip_markdown(match.group(2))
        base = slugify_id(title)
        count = used.get(base, 0)
        used[base] = count + 1
        section_id = base if count == 0 else f"{base}-{count + 1}"
        headings.append((level, title, section_id))
    return headings


def related_pages(page: WikiPage, pages: list[WikiPage], limit: int = 7) -> list[tuple[int, WikiPage, str]]:
    direct_links = set(extract_links(page))
    page_links = {other.rel: set(extract_links(other)) for other in pages}
    page_lens_set = set(page_lenses(page))
    page_stage_set = set(page_pipeline_stages(page))
    page_industry_set = set(page_industries(page))
    scored: list[tuple[int, WikiPage, str]] = []
    for other in pages:
        if other.rel == page.rel:
            continue
        score = 0
        reasons: list[str] = []
        if other.rel in direct_links:
            score += 8
            reasons.append("linked")
        if page.rel in page_links.get(other.rel, set()):
            score += 7
            reasons.append("backlink")
        shared_lenses = page_lens_set & set(page_lenses(other))
        shared_stages = page_stage_set & set(page_pipeline_stages(other))
        shared_industries = page_industry_set & set(page_industries(other))
        if shared_lenses:
            score += 2 * len(shared_lenses)
            reasons.append("lens")
        if shared_stages:
            score += len(shared_stages)
            reasons.append("stage")
        if shared_industries:
            score += 1
            reasons.append("industry")
        if score:
            scored.append((score, other, ", ".join(dict.fromkeys(reasons))))
    scored.sort(key=lambda item: (item[0], item[1].kind == "concept", item[1].title), reverse=True)
    return scored[:limit]


def impact_lens_data(pages: list[WikiPage]) -> list[dict[str, object]]:
    concepts_and_sources = [page for page in pages if page.kind in {"concept", "source"}]
    rows: list[dict[str, object]] = []
    for lens_id, label, description in IMPACT_LENSES:
        linked = [page for page in concepts_and_sources if lens_id in page_lenses(page)]
        high_risk = [page for page in linked if page_risk_level(page) == "high"]
        rows.append(
            {
                "id": lens_id,
                "label": label,
                "description": description,
                "count": len(linked),
                "high_risk": len(high_risk),
                "pages": linked,
            }
        )
    return rows


def pipeline_data(pages: list[WikiPage]) -> list[dict[str, object]]:
    concepts_and_sources = [page for page in pages if page.kind in {"concept", "source"}]
    rows: list[dict[str, object]] = []
    for stage in PIPELINE_STAGES:
        linked = [page for page in concepts_and_sources if stage in page_pipeline_stages(page)]
        rows.append({"stage": stage, "pages": linked, "count": len(linked)})
    return rows


def risk_matrix_data(pages: list[WikiPage]) -> list[dict[str, object]]:
    sources = [page for page in pages if page.kind == "source"]
    rows: list[dict[str, object]] = []
    for industry in INDUSTRIES:
        row: dict[str, object] = {"industry": industry}
        for risk in RISK_LENSES:
            score = 0.0
            for page in sources:
                page_industry_tokens = page_industries(page)
                if page_industry_tokens and industry not in page_industry_tokens:
                    continue
                is_specific = bool(page_industry_tokens) and len(page_industry_tokens) <= 3
                lenses = page_lenses(page)
                text = " ".join(
                    [
                        page.title,
                        section_text(page, "Creative Impact Mapping"),
                        page_summary(page, 520),
                        section_text(page, "Useful Extracts")[:1600],
                    ]
                ).lower()
                lens_hit = any(lens in lenses for lens in RISK_TO_LENSES[risk])
                keyword_hit = any(keyword in text for keyword in RISK_KEYWORDS[risk])
                if keyword_hit:
                    score += 2.0 if is_specific else 0.8
                elif lens_hit:
                    score += 1.0 if is_specific else 0.3
            row[risk] = round(score, 1)
        rows.append(row)
    return rows


def graph_short_label(node: dict[str, str], index: int) -> str:
    label = node["label"]
    rel = node["id"]
    if node["kind"] == "source":
        source_labels = {
            "01-": "Industry",
            "02-": "Music",
            "03-": "Film",
            "04-": "Ads",
            "05-": "Games",
            "06-": "Copyright",
            "07-": "Labor",
            "08-": "Ethics",
        }
        for prefix, short in source_labels.items():
            if Path(rel).name.startswith(prefix):
                return f"S{index}: {short}"
        return f"S{index}"
    concept_labels = {
        "creative-ai-workflows": "Workflow",
        "copyright-and-licensing": "Copyright",
        "creator-labor-and-roles": "Labor",
        "market-structure-and-platforms": "Market",
        "ethics-and-authenticity": "Ethics",
        "music-generation-and-voice": "Music",
        "image-video-and-film-production": "Visual",
    }
    for slug, short in concept_labels.items():
        if slug in rel:
            return short
    if node["kind"] == "workflow":
        return label.replace(" Workflow", "")
    if node["kind"] == "overview":
        return "Overview"
    if node["kind"] == "index":
        return "Index"
    return strip_markdown(label)[:18]


def graph_slug_order(rel: str, ordered_slugs: tuple[str, ...]) -> int:
    for index, slug in enumerate(ordered_slugs):
        if slug in rel:
            return index
    return len(ordered_slugs)


def graph_node_order(node: dict[str, str]) -> tuple[int, int, str]:
    rel = node["id"]
    kind = node["kind"]
    if kind == "source":
        match = re.match(r"(\d+)-", Path(rel).name)
        return (0, int(match.group(1)) if match else 99, rel)
    if kind in {"overview", "index"}:
        return (1, 0 if kind == "overview" else 1, rel)
    if kind == "concept":
        return (2, graph_slug_order(rel, CONCEPT_GRAPH_ORDER), rel)
    if kind == "workflow":
        workflow_order = {"workflows/ingest.md": 0, "workflows/lint.md": 1, "workflows/query.md": 2}
        return (3, workflow_order.get(rel, 99), rel)
    return (4, 99, rel)


def concept_rel_for_slug(concepts: list[dict[str, str]], slug: str) -> str | None:
    for node in concepts:
        if slug in node["id"]:
            return node["id"]
    return None


def fallback_source_concepts(source: WikiPage, concepts: list[dict[str, str]], page_map: dict[str, WikiPage]) -> list[str]:
    source_lenses = set(page_lenses(source))
    source_stages = set(page_pipeline_stages(source))
    source_industries = set(page_industries(source))
    scored: list[tuple[int, str]] = []
    for concept in concepts:
        concept_page = page_map.get(concept["id"])
        if not concept_page:
            continue
        concept_industries = set(page_industries(concept_page))
        score = 0
        score += 4 * len(source_lenses & set(page_lenses(concept_page)))
        score += len(source_stages & set(page_pipeline_stages(concept_page)))
        if source_industries and concept_industries:
            score += 5 if source_industries & concept_industries else 0
        if score:
            scored.append((score, concept["id"]))
    scored.sort(key=lambda item: (item[0], -graph_slug_order(item[1], CONCEPT_GRAPH_ORDER)), reverse=True)
    return [rel for _, rel in scored[:2]]


def semantic_graph_edges(pages: list[WikiPage], display_nodes: list[dict[str, str]]) -> list[dict[str, str]]:
    page_map = {page.rel: page for page in pages}
    node_ids = {node["id"] for node in display_nodes}
    sources = [page for page in pages if page.kind == "source" and page.rel in node_ids]
    concepts = [node for node in display_nodes if node["kind"] == "concept"]
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_edge(source: str, target: str, edge_kind: str) -> None:
        if source not in node_ids or target not in node_ids:
            return
        key = (source, target)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source, "target": target, "kind": edge_kind})

    for source in sources:
        filename = Path(source.rel).name
        hinted_slugs: tuple[str, ...] | None = None
        for prefix, slugs in SOURCE_CONCEPT_HINTS.items():
            if filename.startswith(prefix):
                hinted_slugs = slugs
                break
        targets = [
            rel for rel in (concept_rel_for_slug(concepts, slug) for slug in hinted_slugs or ())
            if rel
        ]
        if not targets:
            targets = fallback_source_concepts(source, concepts, page_map)
        for target in targets[:2]:
            add_edge(source.rel, target, "source-concept")

    for concept in concepts:
        for slug, workflow_targets in CONCEPT_WORKFLOW_HINTS.items():
            if slug not in concept["id"]:
                continue
            for workflow_target in workflow_targets:
                add_edge(concept["id"], workflow_target, "concept-workflow")
            break
    return edges


def graph_display_nodes(nodes: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        node for node in nodes
        if node["kind"] in {"source", "concept", "workflow"}
    ]


def graph_svg(pages: list[WikiPage]) -> str:
    nodes, raw_edges = build_graph(pages)
    if not nodes:
        return '<div class="empty">No graph data yet.</div>'
    display_nodes = graph_display_nodes(nodes)
    columns = {"source": 118, "concept": 480, "workflow": 802}
    grouped: dict[str, list[dict[str, str]]] = {}
    for node in display_nodes:
        grouped.setdefault(node["kind"], []).append(node)
    for kind in grouped:
        grouped[kind].sort(key=graph_node_order)
    positions: dict[str, tuple[int, int]] = {}
    indexes: dict[str, int] = {}
    for kind, items in grouped.items():
        x = columns.get(kind, 310)
        for index, node in enumerate(items):
            y = 78 + index * 62
            positions[node["id"]] = (x, y)
            indexes[node["id"]] = index + 1
    height = max((pos[1] for pos in positions.values()), default=160) + 80
    lines: list[str] = []
    visible_edges = semantic_graph_edges(pages, display_nodes)
    for edge in visible_edges:
        if edge["source"] not in positions or edge["target"] not in positions:
            continue
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        mid = (x1 + x2) / 2
        lines.append(
            f'<path d="M{x1 + 58},{y1} C{mid},{y1} {mid},{y2} {x2 - 58},{y2}" '
            f'class="edge edge-{html.escape(edge["kind"])}" />'
        )
    node_parts: list[str] = []
    for node in display_nodes:
        x, y = positions[node["id"]]
        label = html.escape(graph_short_label(node, indexes[node["id"]]))
        kind = html.escape(node["kind"])
        href = page_url(node["id"])
        node_parts.append(
            f'<a href="{href}"><g class="node node-{kind}">'
            f'<rect x="{x - 56}" y="{y - 18}" width="112" height="36" rx="7" />'
            f'<circle cx="{x - 41}" cy="{y}" r="6" />'
            f'<text x="{x - 28}" y="{y + 5}">{label}</text>'
            f'<title>{html.escape(node["label"])} ({kind})</title>'
            "</g></a>"
        )
    legend = (
        '<text x="70" y="34" class="legend">sources</text>'
        '<text x="446" y="34" class="legend">concepts</text>'
        '<text x="764" y="34" class="legend">workflows</text>'
    )
    source_key_items = []
    for node in grouped.get("source", []):
        source_key_items.append(
            f'<span><strong>{html.escape(graph_short_label(node, indexes[node["id"]]).split(":")[0])}</strong>{html.escape(strip_markdown(node["label"])[:46])}</span>'
        )
    source_key = f'<div class="graph-key">{"".join(source_key_items)}</div>' if source_key_items else ""
    note = (
        f'<div class="graph-note">Showing {len(visible_edges)} curated relationship lines across {len(display_nodes)} displayed nodes. '
        f'{len(raw_edges)} raw Markdown links remain available through page navigation and MCP graph data.</div>'
    )
    return (
        f'<svg class="graph" viewBox="0 0 940 {height}" role="img" '
        f'aria-label="Wiki page graph">{legend}{"".join(lines)}{"".join(node_parts)}</svg>{source_key}{note}'
    )


def page_badges(page: WikiPage) -> str:
    badges = [f'<span class="badge kind-{html.escape(page.kind)}">{html.escape(PAGE_KIND_LABELS.get(page.kind, page.kind.title()))}</span>']
    for lens in page_lenses(page):
        badges.append(f'<span class="badge lens-{html.escape(lens)}">{html.escape(lens.replace("_", " "))}</span>')
    risk = page_risk_level(page)
    badges.append(f'<span class="badge risk-{html.escape(risk)}">risk {html.escape(risk)}</span>')
    return "".join(badges)


def stat_cards(counts: dict[str, int], nodes: int, edges: int) -> str:
    cards = [
        ("Raw Items", counts["raw"], "source materials in raw/"),
        ("Wiki Pages", counts["pages"], "generated Markdown pages"),
        ("Concept Pages", counts["concepts"], "synthesis nodes"),
        ("Graph Edges", edges, f"{nodes} graph nodes"),
        ("High Risk", counts["high_risk"], "pages needing careful review"),
    ]
    return "".join(
        '<article class="stat">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{value}</strong>'
        f'<small>{html.escape(detail)}</small>'
        "</article>"
        for label, value, detail in cards
    )


def sidebar(pages: list[WikiPage], current_rel: str) -> str:
    groups = [
        ("Start", [page for page in pages if page.kind in {"overview", "index", "page"} and "/" not in page.rel]),
        ("Concepts", [page for page in pages if page.kind == "concept"]),
        ("Sources", [page for page in pages if page.kind == "source"]),
        ("Workflows", [page for page in pages if page.kind == "workflow"]),
    ]
    parts = [
        '<aside class="sidebar">',
        '<div class="sidebar-brand"><strong>Wiki Navigator</strong><span>Document map</span></div>',
        '<label class="nav-search"><span>Filter pages</span><input id="navFilter" type="search" placeholder="voice, copyright, workflow" /></label>',
        '<nav class="quick-nav" aria-label="Quick sections">',
        '<a href="/#reader">Reader</a><a href="/#catalog">Catalog</a><a href="/#lenses">Lenses</a><a href="/#graph">Graph</a>',
        "</nav>",
    ]
    for group, items in groups:
        if not items:
            continue
        parts.append(f'<section class="nav-group"><h3>{html.escape(group)} <span>{len(items)}</span></h3><nav>')
        for page in items:
            active = " active" if page.rel == current_rel else ""
            search_blob = html.escape(f"{page.title} {page.kind} {page.rel} {' '.join(page_lenses(page))}", quote=True)
            parts.append(
                f'<a class="page-link{active}" data-nav-item data-search="{search_blob}" href="{page_url(page.rel)}">'
                f'<span>{html.escape(page.title)}</span><small>{html.escape(PAGE_KIND_LABELS.get(page.kind, page.kind))}</small></a>'
            )
        parts.append("</nav></section>")
    parts.append("</aside>")
    return "".join(parts)


def hero_section(profile: dict[str, object], counts: dict[str, int], nodes: int, edges: int, query: str) -> str:
    focus = profile.get("focus_areas", [])
    focus_tags = "".join(f'<span class="focus-tag">{html.escape(str(item))}</span>' for item in focus)
    description = html.escape(str(profile.get("description", "")))
    return (
        '<section class="workspace-hero">'
        '<div class="hero-copy">'
        '<p class="eyebrow">Creative AI LLM Wiki Workbench</p>'
        f'<h1>{html.escape(str(profile.get("name", "Creative AI Wiki")))}</h1>'
        f'<p>{description}</p>'
        f'<div class="focus-tags">{focus_tags}</div>'
        "</div>"
        '<form class="global-search" action="/" method="get">'
        f'<input name="q" value="{html.escape(query, quote=True)}" placeholder="Search the wiki: voice, licensing, workflow..." />'
        '<button type="submit">Search</button>'
        "</form>"
        f'<div class="stats">{stat_cards(counts, nodes, edges)}</div>'
        "</section>"
    )


def search_results_section(query: str, pages: list[WikiPage]) -> str:
    if not query:
        return ""
    results = search_pages(query, pages)
    if not results:
        body = '<div class="empty">No matching wiki pages. Try a lens, industry, or pipeline term.</div>'
    else:
        cards = []
        for score, page, snippet in results:
            cards.append(
                '<article class="result">'
                f'<a href="{page_url(page.rel)}">{html.escape(page.title)}</a>'
                f'<span>{html.escape(PAGE_KIND_LABELS.get(page.kind, page.kind))} · score {score} · {html.escape(page.rel)}</span>'
                f'<div class="badges">{page_badges(page)}</div>'
                f'<p>{html.escape(snippet)}</p>'
                "</article>"
            )
        body = "".join(cards)
    return (
        '<section class="panel search-results">'
        f'<div class="section-head"><h2>Search Results</h2><p>{html.escape(query)}</p></div>'
        f'<div class="result-grid">{body}</div>'
        "</section>"
    )


def document_header(page: WikiPage) -> str:
    metadata_items = [
        ("Path", page.rel),
        ("Kind", PAGE_KIND_LABELS.get(page.kind, page.kind.title())),
        ("Risk", page_risk_level(page).title()),
        ("Read", f"{reading_time(page)} min"),
    ]
    if page.metadata.get("source_count"):
        metadata_items.append(("Sources", page.metadata["source_count"]))
    if page.metadata.get("words"):
        metadata_items.append(("Words", page.metadata["words"]))
    rows = "".join(
        f'<div><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in metadata_items
    )
    return (
        '<header class="document-head">'
        '<div>'
        f'<span class="doc-path">{html.escape(page.rel)}</span>'
        f'<h2>{html.escape(page.title)}</h2>'
        f'<p>{html.escape(page_summary(page))}</p>'
        f'<div class="document-badges">{page_badges(page)}</div>'
        "</div>"
        f'<div class="doc-meta-grid">{rows}</div>'
        "</header>"
    )


def context_panel(page: WikiPage, pages: list[WikiPage]) -> str:
    headings = extract_headings(page)
    outline = "".join(
        f'<a class="level-{level}" href="#{html.escape(section_id)}">{html.escape(title)}</a>'
        for level, title, section_id in headings[:10]
    ) or '<span class="muted">No document sections found.</span>'
    related = related_pages(page, pages)
    related_html = "".join(
        '<a class="related-link" href="{}"><strong>{}</strong><span>{} · {}</span></a>'.format(
            page_url(other.rel),
            html.escape(other.title),
            html.escape(PAGE_KIND_LABELS.get(other.kind, other.kind.title())),
            html.escape(reason),
        )
        for _, other, reason in related
    ) or '<span class="muted">No related pages yet.</span>'
    lenses = "".join(
        f'<a class="chip" href="{url_with(lens=lens)}#catalog">{html.escape(lens.replace("_", " "))}</a>'
        for lens in page_lenses(page)
    ) or '<span class="muted">No lens metadata.</span>'
    stages = "".join(
        f'<a class="chip" href="{url_with(stage=stage)}#catalog">{html.escape(stage)}</a>'
        for stage in page_pipeline_stages(page)
    ) or '<span class="muted">No pipeline metadata.</span>'
    industries = "".join(
        f'<a class="chip" href="{url_with(industry=industry)}#catalog">{html.escape(industry)}</a>'
        for industry in page_industries(page)
    ) or '<span class="muted">No industry metadata.</span>'
    raw_path = page.metadata.get("raw_path")
    raw = f'<code>{html.escape(raw_path)}</code>' if raw_path else '<span class="muted">Not a raw-source page.</span>'
    return (
        '<aside class="doc-context">'
        '<section><h3>Outline</h3><nav class="outline-nav">' + outline + "</nav></section>"
        '<section><h3>Related Pages</h3><div class="related-list">' + related_html + "</div></section>"
        '<section><h3>Analysis Tags</h3><div class="chip-row">' + lenses + '</div><div class="chip-row">' + stages + '</div><div class="chip-row">' + industries + "</div></section>"
        '<section><h3>Source Trail</h3><p>' + raw + "</p></section>"
        "</aside>"
    )


def reader_section(current: WikiPage | None, pages: list[WikiPage], current_rel: str) -> str:
    if current is None:
        return '<section id="reader" class="reader-grid"><div class="empty">No wiki pages found. Run the compiler first.</div></section>'
    return (
        '<section id="reader" class="reader-grid">'
        '<article class="document">'
        f'{document_header(current)}'
        '<div class="reader-tools">'
        '<button type="button" data-doc-action="focus">Focus View</button>'
        '<button type="button" data-doc-action="expand">Expand All</button>'
        "</div>"
        f'<div class="document-body">{render_markdown(current.text, current.rel)}</div>'
        "</article>"
        f'{context_panel(current, pages)}'
        "</section>"
    )


def impact_lens_section(pages: list[WikiPage]) -> str:
    cards = []
    for row in impact_lens_data(pages):
        page_links = "".join(
            f'<a href="{page_url(page.rel)}">{html.escape(page.title)}</a>'
            for page in row["pages"][:4]
        )
        cards.append(
            '<article class="lens-card">'
            f'<a class="card-filter" href="{url_with(lens=str(row["id"]))}#catalog">Filter</a>'
            f'<div class="lens-card-head"><span>{html.escape(str(row["label"]))}</span><strong>{row["count"]}</strong></div>'
            f'<p>{html.escape(str(row["description"]))}</p>'
            f'<div class="lens-risk">{row["high_risk"]} high-risk pages</div>'
            f'<div class="lens-links">{page_links or "<span>No pages yet</span>"}</div>'
            "</article>"
        )
    return (
        '<section id="lenses" class="analysis-section">'
        '<div class="section-head"><h2>Creative Impact Lens</h2>'
        '<p>Five lenses organize how each source affects creative work, rights, labor, markets, and trust.</p></div>'
        f'<div class="lens-grid">{"".join(cards)}</div>'
        "</section>"
    )


def pipeline_section(pages: list[WikiPage]) -> str:
    rows = pipeline_data(pages)
    max_count = max((int(row["count"]) for row in rows), default=1) or 1
    items = []
    for row in rows:
        width = 18 + int(row["count"]) / max_count * 82
        page_links = "".join(
            f'<a href="{page_url(page.rel)}">{html.escape(page.title)}</a>'
            for page in row["pages"][:3]
        )
        items.append(
            '<article class="pipeline-stage">'
            f'<a class="card-filter" href="{url_with(stage=str(row["stage"]))}#catalog">Filter</a>'
            f'<div class="stage-title"><strong>{html.escape(str(row["stage"]).title())}</strong><span>{row["count"]} pages</span></div>'
            f'<div class="stage-bar"><i style="width:{width:.0f}%"></i></div>'
            f'<div class="stage-links">{page_links or "<span>Waiting for sources</span>"}</div>'
            "</article>"
        )
    return (
        '<section class="analysis-section">'
        '<div class="section-head"><h2>Production Pipeline</h2>'
        '<p>Pages are placed along the creative production flow so readers can see where AI changes work.</p></div>'
        f'<div class="pipeline-grid">{"".join(items)}</div>'
        "</section>"
    )


def risk_label(score: float) -> tuple[str, str, int]:
    if score >= 6:
        return "Focus", "high", 100
    if score >= 4:
        return "Watch", "medium", 68
    if score > 0:
        return "Signal", "low", 38
    return "Clear", "none", 8


def risk_matrix_section(pages: list[WikiPage]) -> str:
    header = "".join(f"<th>{html.escape(risk.title())}</th>" for risk in RISK_LENSES)
    rows = []
    for row in risk_matrix_data(pages):
        cells = []
        for risk in RISK_LENSES:
            score = float(row[risk])
            label, level, width = risk_label(score)
            cells.append(
                f'<td class="matrix-{level}">'
                f'<span class="matrix-label">{label}</span>'
                f'<i class="matrix-bar" style="--score:{width}%"></i>'
                f'<small>{score:g}</small>'
                "</td>"
            )
        rows.append(f'<tr><th>{html.escape(str(row["industry"]).title())}</th>{"".join(cells)}</tr>')
    return (
        '<section class="analysis-section">'
        '<div class="section-head"><h2>Review Priority Matrix</h2>'
        '<p>Weighted signals from source pages. Focus means the topic needs review before reuse or publication.</p></div>'
        '<div class="matrix-scroll"><table class="risk-matrix">'
        f'<thead><tr><th>Industry</th>{header}</tr></thead><tbody>{"".join(rows)}</tbody>'
        "</table></div></section>"
    )


def graph_section(pages: list[WikiPage]) -> str:
    nodes, edges = build_graph(pages)
    display_nodes = graph_display_nodes(nodes)
    display_edges = semantic_graph_edges(pages, display_nodes)
    return (
        '<section id="graph" class="graph-wrap">'
        '<div class="graph-head">'
        '<div><h2>Source-Concept Graph</h2><p>Curated relationship lines show how source materials feed concept synthesis and wiki workflows.</p></div>'
        f'<span>{len(display_nodes)} shown · {len(display_edges)} lines · {len(edges)} raw links</span>'
        "</div>"
        f"{graph_svg(pages)}"
        "</section>"
    )


def page_matches(page: WikiPage, filters: dict[str, str], query: str) -> bool:
    if filters.get("kind") and page.kind != filters["kind"]:
        return False
    if filters.get("lens") and filters["lens"] not in page_lenses(page):
        return False
    if filters.get("stage") and filters["stage"] not in page_pipeline_stages(page):
        return False
    if filters.get("industry") and filters["industry"] not in page_industries(page):
        return False
    if filters.get("risk") and filters["risk"] != page_risk_level(page):
        return False
    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) > 1]
    if terms and not all(term in page.text.lower() for term in terms):
        return False
    return True


def filter_link(label: str, params: dict[str, str], active: bool = False) -> str:
    cls = "filter-pill active" if active else "filter-pill"
    return f'<a class="{cls}" data-filter-link="catalog" href="{url_with(**params)}#catalog">{html.escape(label)}</a>'


def catalog_filters(filters: dict[str, str], query: str) -> str:
    kind_filters = [filter_link("All", {"q": query}, not any(filters.values()))]
    for kind in ("concept", "source", "workflow"):
        kind_filters.append(filter_link(PAGE_KIND_LABELS[kind], {"kind": kind, "q": query}, filters.get("kind") == kind))
    lens_filters = [
        filter_link(label, {"lens": lens_id, "q": query}, filters.get("lens") == lens_id)
        for lens_id, label, _ in IMPACT_LENSES
    ]
    stage_filters = [
        filter_link(stage.title(), {"stage": stage, "q": query}, filters.get("stage") == stage)
        for stage in PIPELINE_STAGES
    ]
    risk_filters = [
        filter_link(risk.title(), {"risk": risk, "q": query}, filters.get("risk") == risk)
        for risk in ("high", "medium", "low", "unknown")
    ]
    return (
        '<div class="catalog-filters">'
        '<div><span>Type</span>' + "".join(kind_filters) + "</div>"
        '<div><span>Lens</span>' + "".join(lens_filters) + "</div>"
        '<div><span>Pipeline</span>' + "".join(stage_filters) + "</div>"
        '<div><span>Risk</span>' + "".join(risk_filters) + "</div>"
        "</div>"
    )


def catalog_section(pages: list[WikiPage], filters: dict[str, str], query: str) -> str:
    filtered = [page for page in pages if page_matches(page, filters, query)]
    if not filtered:
        body = '<div class="empty">No pages match the current filters.</div>'
    else:
        cards = []
        for page in filtered:
            summary = page_summary(page, 130)
            cards.append(
                '<article class="catalog-card">'
                f'<div><a href="{page_url(page.rel)}">{html.escape(page.title)}</a><span>{html.escape(page.rel)}</span></div>'
                f'<p class="catalog-summary">{html.escape(summary)}</p>'
                f'<div class="badges">{page_badges(page)}</div>'
                "</article>"
            )
        body = "".join(cards)
    return (
        '<section id="catalog" class="catalog-section">'
        f'<div class="section-head"><h2>Wiki Catalog</h2><p>{len(filtered)} pages shown from {len(pages)} total pages.</p></div>'
        f'{catalog_filters(filters, query)}'
        f'<div class="catalog-grid">{body}</div>'
        "</section>"
    )


def profile_footer(profile: dict[str, object]) -> str:
    pinned = profile.get("pinned_pages", [])
    pinned_html = "".join(f"<code>{html.escape(str(item))}</code>" for item in pinned)
    persona = html.escape(str(profile.get("persona", "reader")))
    domain = html.escape(str(profile.get("domain", "Markdown Knowledge Base")))
    return (
        '<section class="profile-strip">'
        f'<div><span>Persona</span><strong>{persona}</strong></div>'
        f'<div><span>Domain</span><strong>{domain}</strong></div>'
        f'<div><span>Pinned</span><p>{pinned_html}</p></div>'
        "</section>"
    )


def render_app(current_rel: str, query: str = "", filters: dict[str, str] | None = None) -> str:
    pages = iter_pages()
    profile = load_profile()
    page_map = {page.rel: page for page in pages}
    current = page_map.get(current_rel) or page_map.get("overview.md")
    counts = page_counts(pages)
    nodes, edges = build_graph(pages)
    filters = filters or {}
    app_title = html.escape(str(profile.get("name", "Creative AI Wiki")))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{app_title}</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <div class="app-shell">
    {sidebar(pages, current_rel)}
    <main class="content">
      {hero_section(profile, counts, len(nodes), len(edges), query)}
      {search_results_section(query, pages)}
      {reader_section(current, pages, current_rel)}
      <div class="insight-grid">
        {impact_lens_section(pages)}
        {pipeline_section(pages)}
      </div>
      {risk_matrix_section(pages)}
      {graph_section(pages)}
      {catalog_section(pages, filters, query)}
      {profile_footer(profile)}
    </main>
  </div>
  <script src="/static/app.js"></script>
</body>
</html>"""


class WikiHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/static/style.css":
            self.send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/static/app.js":
            self.send_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        params = parse_qs(parsed.query)
        if parsed.path == "/api/graph":
            pages = iter_pages()
            nodes, edges = build_graph(pages)
            self.send_json({"nodes": nodes, "edges": edges})
            return
        if parsed.path == "/api/profile":
            self.send_json(load_profile())
            return
        if parsed.path == "/api/impact-lenses":
            pages = iter_pages()
            payload = [
                {
                    "id": row["id"],
                    "label": row["label"],
                    "description": row["description"],
                    "count": row["count"],
                    "high_risk": row["high_risk"],
                    "pages": [
                        {"rel": page.rel, "title": page.title, "kind": page.kind}
                        for page in row["pages"]
                    ],
                }
                for row in impact_lens_data(pages)
            ]
            self.send_json(payload)
            return
        if parsed.path == "/api/pipeline":
            pages = iter_pages()
            self.send_json(
                [
                    {
                        "stage": row["stage"],
                        "count": row["count"],
                        "pages": [
                            {"rel": page.rel, "title": page.title, "kind": page.kind}
                            for page in row["pages"]
                        ],
                    }
                    for row in pipeline_data(pages)
                ]
            )
            return
        if parsed.path == "/api/risk-matrix":
            self.send_json(risk_matrix_data(iter_pages()))
            return
        if parsed.path == "/api/catalog":
            pages = iter_pages()
            self.send_json(
                [
                    {
                        "rel": page.rel,
                        "title": page.title,
                        "kind": page.kind,
                        "risk": page_risk_level(page),
                        "lenses": page_lenses(page),
                        "pipeline_stages": page_pipeline_stages(page),
                        "industries": page_industries(page),
                        "summary": page_summary(page),
                    }
                    for page in pages
                ]
            )
            return
        if parsed.path in {"/", "/page"}:
            current_rel = safe_page_rel(params.get("path", ["overview.md"])[0])
            query = params.get("q", [""])[0].strip()
            filters = {
                key: params.get(key, [""])[0].strip()
                for key in ("kind", "lens", "stage", "industry", "risk")
            }
            self.send_html(render_app(current_rel, query, filters))
            return
        self.send_error(404, "Not found")

    def send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404, "Not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def check() -> int:
    pages = iter_pages()
    profile = load_profile()
    nodes, edges = build_graph(pages)
    lenses = impact_lens_data(pages)
    pipeline = pipeline_data(pages)
    matrix = risk_matrix_data(pages)
    catalog = [
        page for page in pages if page.kind in {"overview", "index", "concept", "source", "workflow", "page"}
    ]
    html_body = render_app("overview.md")
    print(f"Wiki directory: {WIKI_DIR}")
    print(f"Pages: {len(pages)}")
    print(f"Catalog pages: {len(catalog)}")
    print(f"Graph nodes: {len(nodes)}")
    print(f"Graph edges: {len(edges)}")
    print(f"Impact lenses: {len(lenses)}")
    print(f"Pipeline stages: {len(pipeline)}")
    print(f"Risk matrix rows: {len(matrix)}")
    print(f"Rendered HTML bytes: {len(html_body.encode('utf-8'))}")
    print(f"Profile: {profile.get('name', 'Personal LLM Wiki')}")
    return 0 if pages and catalog and nodes else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Local viewer for the Markdown LLM Wiki.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    parser.add_argument("--check", action="store_true", help="Print viewer readiness and exit.")
    args = parser.parse_args()
    if args.check:
        return check()
    server = ThreadingHTTPServer((args.host, args.port), WikiHandler)
    print(f"Serving LLM Wiki viewer at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
