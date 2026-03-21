import logging
from datetime import datetime, timedelta, timezone

import asyncio
from functools import partial

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# ── AI 글로벌 뉴스 소스 ──────────────────────────────────────
# Hacker News API (커뮤니티 upvote 기반 랭킹)
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# AI 관련 키워드 (Hacker News 필터용)
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "gpt", "llm", "chatgpt", "claude", "openai", "anthropic", "gemini",
    "neural", "transformer", "diffusion", "generative", "copilot",
    "langchain", "rag", "fine-tun", "embedding", "multimodal",
    "midjourney", "stable diffusion", "sora", "reasoning",
]

# Google News AI RSS (Google 자체 랭킹)
GOOGLE_NEWS_AI_RSS = (
    "https://news.google.com/rss/search?"
    "q=artificial+intelligence+OR+AI+OR+machine+learning+OR+LLM"
    "&hl=en-US&gl=US&ceid=US:en"
)

# ── 네이버 섹션 뉴스 ──────────────────────────────────────────
NAVER_SECTION_URL = "https://news.naver.com/section/{}"
NAVER_SECTION_IDS = {
    "politics": 100,
    "economy": 101,
    "society": 102,
}

# 카테고리 정의
NEWS_CATEGORIES = {
    "ai": {"emoji": "🤖", "label": "AI 뉴스", "translate": True},
    "politics": {"emoji": "🏛️", "label": "정치 뉴스", "translate": False},
    "economy": {"emoji": "💰", "label": "경제 뉴스", "translate": False},
    "society": {"emoji": "🏘️", "label": "사회 뉴스", "translate": False},
}

MAX_TOTAL_ITEMS = 10
HN_FETCH_TOP_N = 50  # 상위 50개에서 AI 관련 필터링


# ── Hacker News ──────────────────────────────────────────────

def _is_ai_related(title: str) -> bool:
    """제목에 AI 관련 키워드가 포함되어 있는지 확인"""
    lower = title.lower()
    return any(kw in lower for kw in AI_KEYWORDS)


async def _fetch_hn_ai_news(session: aiohttp.ClientSession) -> list[dict]:
    """Hacker News 상위 스토리에서 AI 관련 기사 추출"""
    try:
        async with session.get(
            HN_TOP_STORIES_URL, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            story_ids = await resp.json()
    except Exception as e:
        logger.warning("Hacker News 상위 스토리 수집 실패: %s", e)
        return []

    story_ids = story_ids[:HN_FETCH_TOP_N]
    items = []

    # 동시에 가져오기
    tasks = []
    for sid in story_ids:
        tasks.append(_fetch_hn_item(session, sid))
    results = await asyncio.gather(*tasks)

    for item in results:
        if item and item.get("title") and _is_ai_related(item["title"]):
            url = item.get("url", f"https://news.ycombinator.com/item?id={item['id']}")
            score = item.get("score", 0)
            published = None
            if item.get("time"):
                published = datetime.fromtimestamp(item["time"], tz=timezone.utc)
            items.append({
                "source": f"HN (⬆{score})",
                "title": item["title"],
                "link": url,
                "published": published,
                "score": score,
            })

    # upvote 순으로 정렬 (이슈된 순)
    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:7]  # HN에서 최대 7개


async def _fetch_hn_item(session: aiohttp.ClientSession, item_id: int) -> dict | None:
    try:
        async with session.get(
            HN_ITEM_URL.format(item_id),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return await resp.json()
    except Exception:
        return None


# ── Google News RSS ──────────────────────────────────────────

async def _fetch_google_news_ai(session: aiohttp.ClientSession) -> list[dict]:
    """Google News AI RSS에서 기사 수집"""
    try:
        async with session.get(
            GOOGLE_NEWS_AI_RSS, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            text = await resp.text()
        feed = feedparser.parse(text)
        items = []
        for entry in feed.entries[:10]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            items.append({
                "source": "Google News",
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": published,
                "score": 0,
            })
        return items
    except Exception as e:
        logger.warning("Google News AI RSS 수집 실패: %s", e)
        return []


# ── AI 뉴스 통합 ─────────────────────────────────────────────

async def _collect_ai_news() -> list[dict]:
    """Hacker News + Google News에서 AI 뉴스 수집"""
    async with aiohttp.ClientSession() as session:
        hn_items, gn_items = await asyncio.gather(
            _fetch_hn_ai_news(session),
            _fetch_google_news_ai(session),
        )

    # HN 기사 우선, Google News로 보충
    all_items = hn_items.copy()

    # 중복 제거하면서 Google News 추가
    seen_titles = {item["title"].lower() for item in all_items}
    for item in gn_items:
        if item["title"].lower() not in seen_titles:
            seen_titles.add(item["title"].lower())
            all_items.append(item)

    result = all_items[:MAX_TOTAL_ITEMS]
    await _translate_titles(result)
    return result


# ── 네이버 랭킹 뉴스 ────────────────────────────────────────

async def _collect_naver_section(category: str) -> list[dict]:
    """네이버 섹션 뉴스에서 카테고리별 기사 수집"""
    section_id = NAVER_SECTION_IDS.get(category)
    if section_id is None:
        return []

    url = NAVER_SECTION_URL.format(section_id)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                html = await resp.text()
    except Exception as e:
        logger.warning("네이버 섹션 뉴스 수집 실패 (%s): %s", category, e)
        return []

    return _parse_naver_section(html)


def _parse_naver_section(html: str) -> list[dict]:
    """네이버 섹션 뉴스 HTML 파싱"""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    now = datetime.now(KST)

    for article in soup.select(".sa_item"):
        title_tag = article.select_one(".sa_text_title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if not title or not href:
            continue

        press_tag = article.select_one(".sa_text_press")
        press_name = press_tag.get_text(strip=True) if press_tag else "네이버"

        items.append({
            "source": press_name,
            "title": title,
            "link": href,
            "published": now,
        })

    # 중복 제거
    seen = set()
    unique = []
    for item in items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)

    return unique[:MAX_TOTAL_ITEMS]


# ── 공통 함수 ────────────────────────────────────────────────

async def fetch_ai_news() -> list[dict]:
    return await _collect_ai_news()


async def fetch_news_by_category(category: str) -> list[dict]:
    """카테고리별 뉴스 수집"""
    if category not in NEWS_CATEGORIES:
        return []

    if category == "ai":
        return await _collect_ai_news()

    return await _collect_naver_section(category)


async def _translate_titles(items: list[dict]) -> list[dict]:
    """제목들을 한글로 번역"""
    translator = GoogleTranslator(source="en", target="ko")
    loop = asyncio.get_event_loop()
    for item in items:
        try:
            item["title_ko"] = await loop.run_in_executor(
                None, partial(translator.translate, item["title"])
            )
        except Exception as e:
            logger.warning("번역 실패: %s", e)
            item["title_ko"] = item["title"]
    return items


def format_news(items: list[dict], category: str = "ai") -> str:
    cat = NEWS_CATEGORIES.get(category, NEWS_CATEGORIES["ai"])
    emoji = cat["emoji"]
    label = cat["label"]

    if not items:
        return f"{emoji} 오늘의 {label}를 수집하지 못했습니다."

    today = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"{emoji} {label} ({today})\n"]

    for i, item in enumerate(items, 1):
        time_str = ""
        if item.get("published"):
            kst_time = item["published"].astimezone(KST)
            time_str = f" · {kst_time.strftime('%H:%M')}"
        title = item.get("title_ko", item["title"])
        lines.append(f"{i}. [{item['source']}{time_str}]")
        lines.append(f"   {title}")
        lines.append(f"   {item['link']}\n")

    return "\n".join(lines)
