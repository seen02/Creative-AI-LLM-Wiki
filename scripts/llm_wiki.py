from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
CACHE_DIR = ROOT / ".wiki_cache" / "text"
PdfReader: Any | None = None


@dataclass(frozen=True)
class SourceDoc:
    number: int
    title: str
    slug: str
    source_path: Path
    source_page: Path
    text_path: Path
    pages: int
    words: int
    text: str


@dataclass(frozen=True)
class Concept:
    slug: str
    title: str
    summary: str
    keywords: tuple[str, ...]
    questions: tuple[str, ...]
    lenses: tuple[str, ...]
    pipeline_stages: tuple[str, ...]
    industries: tuple[str, ...]
    risk_level: str


CONCEPTS = (
    Concept(
        slug="creative-ai-workflows",
        title="Creative AI Workflows",
        summary=(
            "Creative AI workflows describe how generative models become part of production "
            "pipelines for ideation, drafting, asset generation, editing, review, and distribution."
        ),
        keywords=("workflow", "pipeline", "production", "creative process", "human-in-the-loop", "editing"),
        questions=(
            "Where does AI enter the creative pipeline?",
            "Which production steps still require human judgment?",
        ),
        lenses=("workflow",),
        pipeline_stages=("research", "ideation", "generation", "editing", "review", "distribution"),
        industries=("music", "image", "video", "film", "advertising", "game"),
        risk_level="medium",
    ),
    Concept(
        slug="copyright-and-licensing",
        title="Copyright and Licensing",
        summary=(
            "Copyright and licensing issues appear when models are trained on creative works, "
            "imitate styles, synthesize voices or likenesses, and generate outputs for commercial use."
        ),
        keywords=("copyright", "licensing", "training data", "fair use", "style", "voice", "likeness"),
        questions=(
            "What rights are implicated by training data?",
            "When do style imitation, voice cloning, or likeness synthesis create risk?",
        ),
        lenses=("copyright",),
        pipeline_stages=("generation", "distribution"),
        industries=("music", "image", "video", "film", "advertising", "game"),
        risk_level="high",
    ),
    Concept(
        slug="creator-labor-and-roles",
        title="Creator Labor and Roles",
        summary=(
            "Creator labor and roles focus on how AI tools change responsibilities, bargaining power, "
            "skill requirements, and collaboration patterns for creative workers."
        ),
        keywords=("creator", "artist", "labor", "job", "worker", "role", "automation", "augmentation"),
        questions=(
            "Which creative tasks are augmented by AI tools?",
            "Which creative roles are at risk of automation or commoditization?",
        ),
        lenses=("creator_labor",),
        pipeline_stages=("ideation", "generation", "editing", "review"),
        industries=("music", "image", "video", "film", "advertising", "game"),
        risk_level="medium",
    ),
    Concept(
        slug="market-structure-and-platforms",
        title="Market Structure and Platforms",
        summary=(
            "Market structure and platforms examine how generative AI changes value capture among "
            "model providers, creative tools, studios, platforms, independent creators, and audiences."
        ),
        keywords=("platform", "market", "subscription", "distribution", "studio", "tool vendor", "value chain"),
        questions=(
            "Do AI tools lower barriers to entry or centralize power around model providers?",
            "How do platform rules and subscriptions affect creators?",
        ),
        lenses=("market_platform",),
        pipeline_stages=("distribution",),
        industries=("music", "image", "video", "film", "advertising", "game"),
        risk_level="medium",
    ),
    Concept(
        slug="ethics-and-authenticity",
        title="Ethics and Authenticity",
        summary=(
            "Ethics and authenticity cover consent, disclosure, synthetic media labeling, bias, "
            "cultural appropriation, misinformation, and audience trust."
        ),
        keywords=("ethics", "authenticity", "consent", "disclosure", "synthetic media", "bias", "trust"),
        questions=(
            "When should AI involvement be disclosed?",
            "What consent is needed for voice, likeness, or style-based generation?",
        ),
        lenses=("ethics_authenticity",),
        pipeline_stages=("review", "distribution"),
        industries=("music", "image", "video", "film", "advertising", "game"),
        risk_level="high",
    ),
    Concept(
        slug="music-generation-and-voice",
        title="Music Generation and Voice",
        summary=(
            "Music generation and voice synthesis cover AI-assisted composition, sound design, "
            "vocal cloning, performer rights, and distribution issues in music."
        ),
        keywords=("music", "song", "voice", "vocal", "sound", "audio", "performer", "singer"),
        questions=(
            "How do AI-generated songs affect musicians and performers?",
            "What consent and licensing issues arise from voice synthesis?",
        ),
        lenses=("workflow", "copyright", "ethics_authenticity"),
        pipeline_stages=("ideation", "generation", "review", "distribution"),
        industries=("music",),
        risk_level="high",
    ),
    Concept(
        slug="image-video-and-film-production",
        title="Image, Video, and Film Production",
        summary=(
            "Image, video, and film production focuses on generated visuals, previsualization, "
            "editing assistance, synthetic actors, advertising assets, and production cost shifts."
        ),
        keywords=("image", "video", "film", "movie", "advertising", "visual", "previsualization", "editing"),
        questions=(
            "Where do AI-generated visuals fit into film and advertising workflows?",
            "How do synthetic performers or generated scenes affect production economics?",
        ),
        lenses=("workflow", "copyright", "creator_labor", "ethics_authenticity"),
        pipeline_stages=("research", "ideation", "generation", "editing", "review", "distribution"),
        industries=("image", "video", "film", "advertising", "game"),
        risk_level="high",
    ),
)

PIPELINE_ORDER = ("research", "ideation", "generation", "editing", "review", "distribution")
INDUSTRY_ORDER = ("music", "image", "video", "film", "advertising", "game")

KEYWORD_ALIASES = {
    "creative-ai-workflows": (
        "워크플로우", "파이프라인", "프로덕션", "제작", "공정", "운영화",
        "아이디어", "브레인스토밍", "편집", "검토", "배포", "하이브리드",
        "오케스트레이션", "자동화", "생산성",
    ),
    "copyright-and-licensing": (
        "저작권", "라이선스", "라이선싱", "학습 데이터", "훈련 데이터", "공정이용",
        "공정 이용", "텍스트 및 데이터 마이닝", "tdm", "퍼블리시티권", "초상",
        "목소리", "보이스", "스타일", "권리", "등록", "소송", "규제",
    ),
    "creator-labor-and-roles": (
        "창작자", "노동", "노동자", "직무", "일자리", "고용", "노조", "노동조합",
        "작가", "아티스트", "디자이너", "개발자", "자동화", "대체", "숙련",
        "프롬프트", "큐레이터", "편곡자", "검토자",
    ),
    "market-structure-and-platforms": (
        "시장", "플랫폼", "구독", "스튜디오", "에이전시", "모델 제공자", "벤더",
        "가치", "수익", "비즈니스 모델", "클라우드", "인프라", "가격", "분배",
        "독점", "집중",
    ),
    "ethics-and-authenticity": (
        "윤리", "진정성", "동의", "고지", "공개", "투명성", "합성 미디어",
        "신뢰", "편향", "허위정보", "딥페이크", "라벨", "표시", "출처",
        "브랜드 안전", "브랜드 세이프티",
    ),
    "music-generation-and-voice": (
        "음악", "음원", "음향", "오디오", "작곡", "멜로디", "가사", "보컬",
        "목소리", "보이스", "클로닝", "가수", "퍼포머", "연주자", "suno", "udio",
    ),
    "image-video-and-film-production": (
        "이미지", "영상", "비디오", "영화", "시각", "시각 예술", "광고", "게임",
        "스토리보드", "프리비주얼", "프리비주얼라이제이션", "vfx", "합성 배우",
        "배경", "콘셉트 아트", "에셋", "3d", "월드 모델",
    ),
}

SOURCE_CONCEPT_HINTS = {
    "creative-industries": (
        "creative-ai-workflows",
        "market-structure-and-platforms",
        "creator-labor-and-roles",
        "copyright-and-licensing",
        "ethics-and-authenticity",
        "music-generation-and-voice",
        "image-video-and-film-production",
    ),
    "music": (
        "music-generation-and-voice",
        "copyright-and-licensing",
        "ethics-and-authenticity",
        "creator-labor-and-roles",
        "market-structure-and-platforms",
        "creative-ai-workflows",
    ),
    "film": (
        "image-video-and-film-production",
        "creative-ai-workflows",
        "creator-labor-and-roles",
        "ethics-and-authenticity",
        "copyright-and-licensing",
    ),
    "advertising": (
        "image-video-and-film-production",
        "creative-ai-workflows",
        "ethics-and-authenticity",
        "market-structure-and-platforms",
        "copyright-and-licensing",
    ),
    "game": (
        "image-video-and-film-production",
        "creative-ai-workflows",
        "creator-labor-and-roles",
        "copyright-and-licensing",
        "market-structure-and-platforms",
        "ethics-and-authenticity",
    ),
    "copyright": (
        "copyright-and-licensing",
        "ethics-and-authenticity",
        "market-structure-and-platforms",
        "music-generation-and-voice",
    ),
    "creative-labor": (
        "creator-labor-and-roles",
        "market-structure-and-platforms",
        "creative-ai-workflows",
        "copyright-and-licensing",
        "ethics-and-authenticity",
    ),
    "ethics": (
        "ethics-and-authenticity",
        "copyright-and-licensing",
        "music-generation-and-voice",
        "image-video-and-film-production",
    ),
}

SOURCE_INDUSTRY_HINTS = {
    "music": ("music",),
    "film": ("film", "video"),
    "advertising": ("advertising", "image", "video"),
    "game": ("game",),
    "creative-industries": ("music", "image", "video", "film", "advertising", "game"),
    "copyright": ("music", "image", "video", "film", "advertising", "game"),
    "creative-labor": ("music", "image", "video", "film", "advertising", "game"),
    "ethics": ("music", "image", "video", "film", "advertising", "game"),
}

SOURCE_PIPELINE_HINTS = {
    "creative-industries": ("research", "ideation", "generation", "editing", "review", "distribution"),
    "music": ("ideation", "generation", "editing", "review", "distribution"),
    "film": ("research", "ideation", "generation", "editing", "review", "distribution"),
    "advertising": ("ideation", "generation", "review", "distribution"),
    "game": ("ideation", "generation", "editing", "review"),
    "copyright": ("generation", "review", "distribution"),
    "creative-labor": ("ideation", "generation", "editing", "review"),
    "ethics": ("review", "distribution"),
}

CONCEPT_QUESTIONS_KO = {
    "creative-ai-workflows": (
        "AI가 창작 파이프라인의 어느 단계에 들어오는가?",
        "어떤 단계에서 인간의 판단, 편집, 검수가 여전히 필수적인가?",
    ),
    "copyright-and-licensing": (
        "학습 데이터, 산출물, 스타일 모방, 음성·초상 복제 중 어떤 권리가 문제 되는가?",
        "상업적 이용 전에 필요한 라이선스, 동의, 출처 검증은 무엇인가?",
    ),
    "creator-labor-and-roles": (
        "AI가 창작자의 역할을 보조하는가, 대체하는가, 혹은 새 직무로 재편하는가?",
        "생산성 향상과 노동 조건 악화가 동시에 나타나는 지점은 어디인가?",
    ),
    "market-structure-and-platforms": (
        "가치 포획이 창작자보다 플랫폼, 스튜디오, 모델 제공자 쪽으로 이동하는가?",
        "구독형 도구, 라이선스 계약, 데이터 접근권이 시장 구조를 어떻게 바꾸는가?",
    ),
    "ethics-and-authenticity": (
        "AI 사용 사실을 언제, 누구에게, 어떤 방식으로 고지해야 하는가?",
        "동의 없는 음성·초상·스타일 복제가 수용자 신뢰와 인격권에 어떤 위험을 만드는가?",
    ),
    "music-generation-and-voice": (
        "AI 생성 음악과 보이스 클로닝은 음악가, 실연자, 레이블의 권리를 어떻게 재조정하는가?",
        "동의 기반 음성 라이선싱과 무단 복제의 경계는 어떻게 판단해야 하는가?",
    ),
    "image-video-and-film-production": (
        "이미지, 영상, 영화, 광고, 게임 제작에서 AI가 어떤 제작 비용과 시간을 줄이는가?",
        "합성 배우, 생성 에셋, 스타일 모방이 노동권과 저작권에 어떤 위험을 만드는가?",
    ),
}


def csv(values: tuple[str, ...] | list[str]) -> str:
    return ", ".join(values)


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for directory in (
        WIKI_DIR,
        WIKI_DIR / "sources",
        WIKI_DIR / "concepts",
        WIKI_DIR / "workflows",
        CACHE_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "untitled"


def display_title_from_stem(stem: str) -> str:
    stem = re.sub(r"^\d+[\-_. ]+", "", stem)
    stem = re.sub(r"^sample[-_ ]+", "", stem, flags=re.IGNORECASE)
    title = re.sub(r"[-_]+", " ", stem).strip()
    title = title.title()
    title = re.sub(r"\bAi\b", "AI", title)
    return title or "Untitled"


def parse_source_name(path: Path) -> tuple[int, str, str]:
    match = re.match(r"^\s*(\d+)[.\-_ ]+\s*(.+?)\.[^.]+$", path.name, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        title = match.group(2).strip()
    else:
        number = 999
        title = display_title_from_stem(path.stem)
    slug = f"{number:02d}-{slugify(title)}"
    return number, title, slug


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "-")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\\.", ".").replace("\\~", "~")
    text = text.replace("हालांकि", "그러나").replace("हालाँकि", "그러나")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_markdown_inline(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!~|])", r"\1", text)
    text = re.sub(r"(?<=[가-힣A-Za-z\)])\d{1,3}(?=[\.,;:\)\]\s]|$)", "", text)
    return compact(text)


def clean_markdown_text(text: str) -> str:
    cleaned: list[str] = []
    in_code = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        stripped = line.strip()
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if stripped.startswith("|") or re.match(r"^\|?[\s:\-|]+\|?$", stripped):
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            title = strip_markdown_inline(heading.group(2))
            if title:
                if cleaned and cleaned[-1] != "":
                    cleaned.append("")
                cleaned.append(title)
                cleaned.append("")
            continue
        stripped = re.sub(r"^\s*[-*+]\s+", "", stripped)
        stripped = re.sub(r"^\s*\d+[.)]\s+", "", stripped)
        stripped = strip_markdown_inline(stripped)
        if stripped:
            cleaned.append(stripped)
    return normalize_text("\n".join(cleaned))


def source_title_from_text(text: str) -> str | None:
    for paragraph in split_paragraphs(text):
        if 8 <= len(paragraph) <= 160:
            return paragraph
        if len(paragraph) > 160:
            return None
    return None


def concept_keywords(concept: Concept) -> tuple[str, ...]:
    return concept.keywords + KEYWORD_ALIASES.get(concept.slug, ())


def source_hint_keys(source: SourceDoc) -> tuple[str, ...]:
    blob = f"{source.slug} {source.title}".lower()
    keys = [key for key in SOURCE_CONCEPT_HINTS if key in blob]
    if "cinema" in blob or "movie" in blob:
        keys.append("film")
    return tuple(dict.fromkeys(keys))


def require_pdf_reader() -> Any:
    global PdfReader
    if PdfReader is None:
        try:
            from pypdf import PdfReader as ImportedPdfReader
        except ImportError as exc:  # pragma: no cover - user setup path
            raise SystemExit(
                "Missing dependency: pypdf. Run `python -m pip install -r requirements.txt`."
            ) from exc
        PdfReader = ImportedPdfReader
    return PdfReader


def extract_pdf(pdf_path: Path) -> tuple[str, int]:
    reader = require_pdf_reader()(str(pdf_path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = normalize_text(page_text)
        if page_text:
            chunks.append(f"\n\n--- Page {index} ---\n{page_text}")
    return normalize_text("\n".join(chunks)), len(reader.pages)


def raw_source_files() -> list[Path]:
    ignored = {"readme.md", ".gitkeep"}
    supported = {".pdf", ".md", ".txt"}
    return [
        path
        for path in sorted(RAW_DIR.iterdir())
        if path.is_file()
        and path.name.lower() not in ignored
        and path.suffix.lower() in supported
    ] if RAW_DIR.exists() else []


def extract_source(source_path: Path) -> tuple[str, int]:
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(source_path)
    raw_text = source_path.read_text(encoding="utf-8", errors="ignore")
    text = clean_markdown_text(raw_text) if suffix == ".md" else normalize_text(raw_text)
    return text, 1


def load_sources() -> list[SourceDoc]:
    ensure_dirs()
    sources: list[SourceDoc] = []
    for source_path in raw_source_files():
        number, fallback_title, slug = parse_source_name(source_path)
        text, pages = extract_source(source_path)
        title = source_title_from_text(text) or fallback_title
        text_path = CACHE_DIR / f"{slug}.txt"
        text_path.write_text(text + "\n", encoding="utf-8")
        words = len(re.findall(r"\S+", text))
        sources.append(
            SourceDoc(
                number=number,
                title=title,
                slug=slug,
                source_path=source_path,
                source_page=WIKI_DIR / "sources" / f"{slug}.md",
                text_path=text_path,
                pages=pages,
                words=words,
                text=text,
            )
        )
    return sources


def rel(path: Path, base: Path = WIKI_DIR) -> str:
    return path.relative_to(base).as_posix()


def wiki_link(path: Path, title: str, base: Path = WIKI_DIR) -> str:
    return f"[{title}]({rel(path, base)})"


def raw_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def split_paragraphs(text: str) -> list[str]:
    text = re.sub(r"--- Page \d+ ---", " ", text)
    paragraphs = []
    for chunk in re.split(r"\n\s*\n+", text):
        paragraph = compact(chunk)
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    lower = text.lower()
    score = 0
    for keyword in keywords:
        lowered = keyword.lower()
        if not lowered:
            continue
        hits = lower.count(lowered)
        if hits:
            score += hits * (3 if len(keyword) >= 4 else 1)
    return score


def split_sentences(text: str) -> list[str]:
    return [compact(sentence) for sentence in re.split(r"(?<=[.!?])\s+", text) if compact(sentence)]


def fingerprint(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())[:220]


def shorten_clean(text: str, max_chars: int = 520) -> str:
    text = compact(text)
    if len(text) <= max_chars:
        return text
    sentences = split_sentences(text)
    selected: list[str] = []
    total = 0
    for sentence in sentences:
        if total + len(sentence) + 1 > max_chars:
            break
        selected.append(sentence)
        total += len(sentence) + 1
    if selected:
        return " ".join(selected)
    shortened = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened.rstrip(".") + "."


def focused_snippet(paragraph: str, keywords: tuple[str, ...], max_chars: int = 520) -> str:
    if len(paragraph) <= max_chars:
        return paragraph
    sentences = split_sentences(paragraph)
    matching = [sentence for sentence in sentences if keyword_score(sentence, keywords)]
    if matching:
        selected: list[str] = []
        total = 0
        for sentence in matching:
            if total + len(sentence) > max_chars and selected:
                break
            selected.append(sentence)
            total += len(sentence) + 1
        return shorten_clean(" ".join(selected), max_chars)
    return shorten_clean(paragraph, max_chars)


def excerpt_around(text: str, keywords: tuple[str, ...], limit: int = 3) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    for index, paragraph in enumerate(split_paragraphs(text)):
        if len(paragraph) < 80:
            continue
        if paragraph.count(" | ") >= 3:
            continue
        score = keyword_score(paragraph, keywords)
        if score:
            candidates.append((score, index, paragraph))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    excerpts: list[str] = []
    seen: set[str] = set()
    for _, _, paragraph in candidates:
        snippet = focused_snippet(paragraph, keywords)
        key = fingerprint(snippet)
        if key in seen:
            continue
        excerpts.append(snippet)
        seen.add(key)
        if len(excerpts) >= limit:
            break
    return excerpts


def first_signal(text: str, max_chars: int = 760) -> str:
    paragraphs = [
        paragraph for paragraph in split_paragraphs(text)
        if len(paragraph) >= 120 and paragraph.count(" | ") < 3
    ]
    if not paragraphs:
        return shorten_clean(text, max_chars)
    return shorten_clean(paragraphs[0], max_chars)


def hinted_concept_slugs(source: SourceDoc) -> set[str]:
    slugs: set[str] = set()
    for key in source_hint_keys(source):
        slugs.update(SOURCE_CONCEPT_HINTS.get(key, ()))
    return slugs


def source_concept_score(source: SourceDoc, concept: Concept) -> int:
    keywords = concept_keywords(concept)
    text_sample = source.text[:9000]
    score = keyword_score(source.title, keywords) * 30
    score += keyword_score(text_sample, keywords)
    if concept.slug in hinted_concept_slugs(source):
        score += 120
    return score


def source_related_concepts(source: SourceDoc, limit: int = 6) -> list[Concept]:
    scored = [
        (source_concept_score(source, concept), concept)
        for concept in CONCEPTS
    ]
    hinted = hinted_concept_slugs(source)
    selected = [
        (score, concept)
        for score, concept in scored
        if concept.slug in hinted or score >= 24
    ]
    selected.sort(key=lambda item: (-item[0], item[1].title))
    if "creative-industries" not in source.slug:
        selected = selected[:limit]
    return [concept for _, concept in selected]


def source_industries(source: SourceDoc, related: list[Concept]) -> list[str]:
    keys = source_hint_keys(source)
    specific_keys = [key for key in keys if key in {"music", "film", "advertising", "game"}]
    hinted: list[str] = []
    for key in specific_keys or keys:
        hinted.extend(SOURCE_INDUSTRY_HINTS.get(key, ()))
    if hinted:
        return list(dict.fromkeys(hinted))
    inferred = {industry for concept in related for industry in concept.industries}
    return [industry for industry in INDUSTRY_ORDER if industry in inferred]


def source_pipeline_stages(source: SourceDoc, related: list[Concept]) -> list[str]:
    keys = source_hint_keys(source)
    specific_keys = [key for key in keys if key in {"music", "film", "advertising", "game"}]
    stages = []
    for key in specific_keys or keys:
        stages.extend(SOURCE_PIPELINE_HINTS.get(key, ()))
    if not stages:
        stages = [stage for concept in related for stage in concept.pipeline_stages]
    return [stage for stage in PIPELINE_ORDER if stage in set(stages)]


def write_source_pages(sources: list[SourceDoc], stamp: str) -> None:
    source_dir = WIKI_DIR / "sources"
    for old_source_page in source_dir.glob("*.md"):
        old_source_page.unlink()
    for source in sources:
        related = source_related_concepts(source)
        lenses = sorted({lens for concept in related for lens in concept.lenses})
        pipeline_stages = source_pipeline_stages(source, related)
        industries = source_industries(source, related)
        risk_level = "high" if any(concept.risk_level == "high" for concept in related) else "medium" if related else "unknown"
        related_links = (
            "\n".join(
                f"- [{concept.title}](../concepts/{concept.slug}.md)" for concept in related
            )
            or "- No concept mapping yet."
        )
        concept_names = ", ".join(concept.title for concept in related) or "No concept mapping yet"
        excerpts = excerpt_around(source.text, tuple(k for c in related for k in concept_keywords(c)), 5)
        excerpt_lines = "\n".join(f"- {snippet}" for snippet in excerpts) or "- No keyword excerpts found."
        content = f"""---
title: "{source.title}"
kind: source
raw_path: "{raw_rel(source.source_path)}"
pages: {source.pages}
words: {source.words}
compiled_at: "{stamp}"
lenses: "{csv(lenses)}"
pipeline_stages: "{csv(pipeline_stages)}"
industries: "{csv(industries)}"
risk_level: "{risk_level}"
---

# {source.title}

## Source Metadata

- Raw file: `{raw_rel(source.source_path)}`
- Extracted text cache: `{raw_rel(source.text_path)}`
- Page-like count: {source.pages}
- Extracted word-like tokens: {source.words}

## Creative Impact Mapping

- Primary concepts: {concept_names}
- Lenses: {csv(lenses) or "unknown"}
- Pipeline stages: {csv(pipeline_stages) or "unknown"}
- Industries: {csv(industries) or "unknown"}
- Risk level: {risk_level}

## First Signal

{first_signal(source.text)}

## Related Concepts

{related_links}

## Useful Extracts

{excerpt_lines}

## Notes

This page is generated from source text extraction. Review the raw source before relying on exact wording, layout, or diagrams.
"""
        source.source_page.write_text(content, encoding="utf-8")


def evidence_for_concept(concept: Concept, sources: list[SourceDoc]) -> list[tuple[SourceDoc, list[str]]]:
    ranked: list[tuple[int, SourceDoc, list[str]]] = []
    for source in sources:
        excerpts = excerpt_around(source.text, concept_keywords(concept), 3)
        if excerpts:
            score = source_concept_score(source, concept)
            ranked.append((score, source, excerpts))
    ranked.sort(key=lambda item: (-item[0], item[1].number))
    if concept.slug in {"music-generation-and-voice", "image-video-and-film-production"}:
        ranked = ranked[:5]
    elif concept.slug in {"copyright-and-licensing", "creator-labor-and-roles", "ethics-and-authenticity"}:
        ranked = ranked[:6]
    return [(source, excerpts) for _, source, excerpts in ranked]


def concept_key_claims(concept: Concept, source_count: int) -> str:
    lenses = ", ".join(lens.replace("_", " ") for lens in concept.lenses)
    stages = ", ".join(concept.pipeline_stages)
    industries = ", ".join(concept.industries)
    claims = [
        f"`{concept.title}`는 생성형 AI가 창작 생산 과정에 미치는 영향을 설명하기 위한 핵심 분석 축이다.",
        f"현재 위키에서는 {source_count}개의 source 문서가 이 개념의 근거로 연결되어 있다.",
        f"검토할 Creative Impact Lens는 {lenses}이며, 주로 {stages} 단계에서 의미가 크다.",
        f"관련 산업 범위는 {industries}이다.",
    ]
    return "\n".join(f"- {claim}" for claim in claims)


def concept_interpretation(concept: Concept, source_count: int) -> str:
    if source_count == 0:
        return (
            "현재 이 개념을 뒷받침하는 source 문서가 충분하지 않다. 이 페이지는 자리표시자로 보고, "
            "새 자료를 추가하거나 원문을 검토한 뒤 사용해야 한다."
        )
    return (
        "이 페이지의 evidence는 최종 법률·정책 판단이 아니라, 어떤 source가 해당 개념을 다루는지 "
        "보여주는 synthesis map으로 읽어야 한다. 정확한 수치, 판례, 제도명, 권리 판단은 연결된 "
        "source page와 raw 파일에서 다시 확인한다."
    )


def concept_risks_to_review(concept: Concept) -> str:
    risks = []
    if concept.risk_level == "high":
        risks.append("법률, 정책, 공개 발표에 사용할 주장은 반드시 원문 source와 대조한다.")
    if "copyright" in concept.lenses:
        risks.append("학습 데이터, 모델 산출물, 라이선싱, 상업적 이용을 구분해서 검토한다.")
    if "ethics_authenticity" in concept.lenses:
        risks.append("동의, 고지, 라벨링, 수용자 신뢰 문제가 명시적으로 다뤄졌는지 확인한다.")
    if "creator_labor" in concept.lenses:
        risks.append("생산성 향상 주장과 일자리 대체, 협상력, 직무 품질 문제를 분리해서 읽는다.")
    if "market_platform" in concept.lenses:
        risks.append("가치가 창작자, 스튜디오, 플랫폼, 모델 제공자 중 어디로 이동하는지 확인한다.")
    if not risks:
        risks.append("source evidence가 concept summary를 뒷받침할 만큼 구체적인지 검토한다.")
    return "\n".join(f"- {risk}" for risk in risks)


def write_concept_pages(sources: list[SourceDoc], stamp: str) -> None:
    for concept in CONCEPTS:
        evidence = evidence_for_concept(concept, sources)
        source_count = len(evidence)
        evidence_lines: list[str] = []
        for source, excerpts in evidence:
            source_link = f"[{source.title}](../sources/{source.source_page.name})"
            evidence_lines.append(f"### {source_link}")
            for snippet in excerpts:
                evidence_lines.append(f"- {snippet}")
            evidence_lines.append("")
        evidence_block = "\n".join(evidence_lines).strip() or "No source evidence found yet."
        questions = CONCEPT_QUESTIONS_KO.get(concept.slug, concept.questions)
        question_lines = "\n".join(f"- {question}" for question in questions)
        related = [
            other for other in CONCEPTS if other.slug != concept.slug and set(other.keywords) & set(concept.keywords)
        ]
        related_lines = (
            "\n".join(f"- [{other.title}]({other.slug}.md)" for other in related)
            or "- See [Overview](../overview.md) for the full sequence."
        )
        content = f"""---
title: "{concept.title}"
kind: concept
source_count: {source_count}
compiled_at: "{stamp}"
lenses: "{csv(concept.lenses)}"
pipeline_stages: "{csv(concept.pipeline_stages)}"
industries: "{csv(concept.industries)}"
risk_level: "{concept.risk_level}"
---

# {concept.title}

## Summary

{concept.summary}

## Key Claims

{concept_key_claims(concept, source_count)}

## Source Evidence

{evidence_block}

## Interpretation

{concept_interpretation(concept, source_count)}

## Risks To Review

{concept_risks_to_review(concept)}

## Questions To Ask

{question_lines}

## Related

{related_lines}
"""
        (WIKI_DIR / "concepts" / f"{concept.slug}.md").write_text(content, encoding="utf-8")


def write_overview(sources: list[SourceDoc], stamp: str) -> None:
    source_lines = "\n".join(
        f"{source.number}. [{source.title}](sources/{source.source_page.name})"
        for source in sorted(sources, key=lambda item: item.number)
    ) or "No source pages have been generated yet. Add source files to `raw/` and run the compiler."
    concept_lines = "\n".join(
        f"- [{concept.title}](concepts/{concept.slug}.md)" for concept in CONCEPTS
    )
    content = f"""---
title: "Generative AI and Creative Production Overview"
kind: overview
compiled_at: "{stamp}"
---

# Generative AI and Creative Production Overview

This wiki compiles source materials in `raw/` into a navigable Markdown knowledge base about generative AI and creative production.

## Domain-Level Synthesis

The materials should explain how generative AI changes creative workflows, rights and licensing, creator labor, platform economics, and audience trust across music, images, video, film, advertising, and games.

## Special Analysis Layer

This wiki is organized through Creative Impact Lenses:

- Workflow Impact
- Copyright and Licensing
- Creator Labor
- Market and Platform Structure
- Ethics and Authenticity

The viewer uses this metadata to render a production pipeline, risk matrix, and source-concept graph. MCP tools expose the same structures to an external agent.

## Source Set

{source_lines}

## Core Concepts

{concept_lines}

## Current Boundaries

This wiki is a local research workbench, not a final legal opinion or academic publication. It preserves raw-source traceability, creates source pages, synthesizes concept pages, and exposes the same structures through the viewer and MCP tools. Important legal, policy, and market claims should still be verified against the linked source pages and raw files.
"""
    (WIKI_DIR / "overview.md").write_text(content, encoding="utf-8")


def write_workflows(stamp: str) -> None:
    workflows = {
        "ingest.md": f"""---
title: "Ingest Workflow"
kind: workflow
compiled_at: "{stamp}"
---

# Ingest Workflow

1. Put permitted `.pdf`, `.md`, or `.txt` source files in `raw/`.
2. Run `python scripts/llm_wiki.py compile`.
3. Review `wiki/sources/` for extraction quality.
4. Review `wiki/concepts/` for missing or weak synthesis.
5. Keep `raw/` immutable and append updates to `wiki/log.md`.
""",
        "query.md": f"""---
title: "Query Workflow"
kind: workflow
compiled_at: "{stamp}"
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
""",
        "lint.md": f"""---
title: "Lint Workflow"
kind: workflow
compiled_at: "{stamp}"
---

# Lint Workflow

Run:

```powershell
python scripts/llm_wiki.py lint
```

The MVP lint checks for required directories, core files, and one source page per supported raw source file.
""",
    }
    for filename, content in workflows.items():
        (WIKI_DIR / "workflows" / filename).write_text(content, encoding="utf-8")


def write_index(sources: list[SourceDoc], stamp: str) -> None:
    source_lines = "\n".join(
        f"- [{source.title}](sources/{source.source_page.name}) - {source.pages} pages, {source.words} tokens"
        for source in sorted(sources, key=lambda item: item.number)
    ) or "No source pages have been generated yet."
    concept_lines = "\n".join(
        f"- [{concept.title}](concepts/{concept.slug}.md)" for concept in CONCEPTS
    )
    workflow_lines = "\n".join(
        f"- [{path.stem.title()}](workflows/{path.name})"
        for path in sorted((WIKI_DIR / "workflows").glob("*.md"))
    )
    content = f"""---
title: "Creative AI Wiki Index"
kind: index
compiled_at: "{stamp}"
---

# Creative AI Wiki Index

Updated: {stamp}

## Start Here

- [Overview](overview.md)
- [Maintenance Log](log.md)
- [Operating Schema](../AGENTS.md)
- [Project Rules](../RULES.md)
- [MCP Tool Contract](../schema/mcp-tools.md)

## Concept Pages

{concept_lines}

## Source Pages

{source_lines}

## Workflows

{workflow_lines}

## Domain Views

The local viewer renders the following analysis views:

- Creative Impact Lens
- Production Pipeline
- Risk & Rights Matrix
- Source-Concept Graph

## Commands

```powershell
python scripts/llm_wiki.py compile
python scripts/llm_wiki.py query "copyright voice"
python scripts/llm_wiki.py lint
```
"""
    (WIKI_DIR / "index.md").write_text(content, encoding="utf-8")


def append_log(sources: list[SourceDoc], stamp: str) -> None:
    log_path = WIKI_DIR / "log.md"
    if not log_path.exists():
        log_path.write_text("# LLM Wiki Log\n\n", encoding="utf-8")
    entry = (
        f"## [{stamp}] compile | raw source ingest\n\n"
        f"- Sources compiled: {len(sources)}\n"
        f"- Concept pages: {len(CONCEPTS)}\n"
        f"- Text cache: `{raw_rel(CACHE_DIR)}`\n\n"
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def compile_wiki() -> None:
    stamp = now_stamp()
    sources = load_sources()
    write_source_pages(sources, stamp)
    write_concept_pages(sources, stamp)
    write_overview(sources, stamp)
    write_workflows(stamp)
    write_index(sources, stamp)
    append_log(sources, stamp)
    print(f"Compiled {len(sources)} sources into {WIKI_DIR}")


def status() -> None:
    raw_items = raw_source_files()
    sources = sorted((WIKI_DIR / "sources").glob("*.md"))
    concepts = sorted((WIKI_DIR / "concepts").glob("*.md"))
    print(f"Raw source files: {len(raw_items)}")
    print(f"Source pages: {len(sources)}")
    print(f"Concept pages: {len(concepts)}")
    print(f"Wiki path: {WIKI_DIR}")


def score_text(query_terms: list[str], text: str) -> int:
    lower = text.lower()
    phrase = " ".join(query_terms)
    phrase_score = lower.count(phrase) * 25 if len(query_terms) > 1 else 0
    term_score = sum(lower.count(term) for term in query_terms)
    return phrase_score + term_score


def query_wiki(query: str, limit: int = 8) -> None:
    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) > 1]
    if not terms:
        raise SystemExit("Query must contain at least one searchable term.")
    candidates: list[tuple[int, Path, str]] = []
    for path in list(WIKI_DIR.rglob("*.md")) + list(CACHE_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        score = score_text(terms, text)
        if score:
            snippet = excerpt_around(text, tuple(terms), 1)
            candidates.append((score, path, snippet[0] if snippet else ""))
    candidates.sort(key=lambda item: item[0], reverse=True)
    for score, path, snippet in candidates[:limit]:
        print(f"[{score}] {raw_rel(path)}")
        if snippet:
            print(f"    {snippet}")


def lint() -> int:
    errors: list[str] = []
    for path in (RAW_DIR, WIKI_DIR, WIKI_DIR / "sources", WIKI_DIR / "concepts", WIKI_DIR / "workflows"):
        if not path.exists():
            errors.append(f"Missing required path: {raw_rel(path)}")
    for filename in ("overview.md", "index.md", "log.md"):
        if not (WIKI_DIR / filename).exists():
            errors.append(f"Missing core file: wiki/{filename}")
    for source_path in raw_source_files():
        _, _, slug = parse_source_name(source_path)
        if not (WIKI_DIR / "sources" / f"{slug}.md").exists():
            errors.append(f"Missing source page for {raw_rel(source_path)}")
    if errors:
        print("Lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Lint passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal compiler for this LLM Wiki.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("compile", help="Extract raw source files and regenerate the wiki.")
    subparsers.add_parser("status", help="Print wiki counts.")
    subparsers.add_parser("lint", help="Check required wiki files.")
    query_parser = subparsers.add_parser("query", help="Search generated wiki and extracted text.")
    query_parser.add_argument("text", help="Search query.")
    query_parser.add_argument("--limit", type=int, default=8, help="Maximum results.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.command == "compile":
        compile_wiki()
        return 0
    if args.command == "status":
        status()
        return 0
    if args.command == "query":
        query_wiki(args.text, args.limit)
        return 0
    if args.command == "lint":
        return lint()
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
