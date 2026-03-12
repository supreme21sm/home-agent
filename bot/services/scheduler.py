import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import config
from bot.services.news import fetch_news_by_category, format_news, NEWS_CATEGORIES

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _send_category_news(bot: Bot, category: str) -> None:
    cat = NEWS_CATEGORIES[category]
    logger.info("%s 수집 시작", cat["label"])
    try:
        items = await fetch_news_by_category(category)
        text = format_news(items, category)
        for user_id in config.allowed_users:
            try:
                await bot.send_message(user_id, text, disable_web_page_preview=True)
            except Exception as e:
                logger.warning("뉴스 전송 실패 (user_id=%s): %s", user_id, e)
        logger.info("%s 전송 완료 (%d건)", cat["label"], len(items))
    except Exception as e:
        logger.error("%s 수집 실패: %s", cat["label"], e)


async def _send_all_news(bot: Bot) -> None:
    """모든 카테고리 뉴스를 순차적으로 전송"""
    for category in NEWS_CATEGORIES:
        await _send_category_news(bot, category)
        await asyncio.sleep(2)  # 메시지 간 간격


def start_scheduler(bot: Bot) -> None:
    scheduler.add_job(
        _send_all_news,
        trigger="cron",
        hour=config.news_hour,
        minute=config.news_minute,
        args=[bot],
        id="daily_all_news",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "스케줄러 시작 — 매일 %02d:%02d (KST) 뉴스 전송 (AI/정치/경제/사회)",
        config.news_hour, config.news_minute,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
