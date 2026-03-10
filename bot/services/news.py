import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import feedparser

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# AI/ML 관련 RSS 피드
FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica AI", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
]

MAX_ITEMS_PER_FEED = 3
MAX_TOTAL_ITEMS = 10


async def _fetch_feed(session: aiohttp.ClientSession, name: str, url: str) -> list[dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            text = await resp.text()
        feed = feedparser.parse(text)
        items = []
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            items.append({
                "source": name,
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": published,
            })
        return items
    except Exception as e:
        logger.warning("피드 수집 실패 (%s): %s", name, e)
        return []


async def fetch_ai_news() -> list[dict]:
    all_items: list[dict] = []
    async with aiohttp.ClientSession() as session:
        for name, url in FEEDS:
            items = await _fetch_feed(session, name, url)
            all_items.extend(items)

    # 최근 24시간 내 기사 우선, 없으면 전체에서 선택
    now = datetime.now(timezone.utc)
    recent = [
        item for item in all_items
        if item["published"] and (now - item["published"]).total_seconds() < 86400
    ]

    pool = recent if recent else all_items
    # 중복 제거 (제목 기준)
    seen = set()
    unique = []
    for item in pool:
        key = item["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 최신순 정렬
    unique.sort(key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return unique[:MAX_TOTAL_ITEMS]


def format_news(items: list[dict]) -> str:
    if not items:
        return "📰 오늘의 AI 뉴스를 수집하지 못했습니다."

    today = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"📰 AI 뉴스 ({today})\n"]

    for i, item in enumerate(items, 1):
        time_str = ""
        if item["published"]:
            kst_time = item["published"].astimezone(KST)
            time_str = f" · {kst_time.strftime('%H:%M')}"
        lines.append(f"{i}. [{item['source']}{time_str}]")
        lines.append(f"   {item['title']}")
        lines.append(f"   {item['link']}\n")

    return "\n".join(lines)
