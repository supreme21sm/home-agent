import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import config
from bot.services.news import fetch_ai_news, format_news

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def _send_daily_news(bot: Bot) -> None:
    logger.info("AI 뉴스 수집 시작")
    try:
        items = await fetch_ai_news()
        text = format_news(items)
        for user_id in config.allowed_users:
            try:
                await bot.send_message(user_id, text, disable_web_page_preview=True)
            except Exception as e:
                logger.warning("뉴스 전송 실패 (user_id=%s): %s", user_id, e)
        logger.info("AI 뉴스 전송 완료 (%d건)", len(items))
    except Exception as e:
        logger.error("AI 뉴스 수집 실패: %s", e)


def start_scheduler(bot: Bot) -> None:
    scheduler.add_job(
        _send_daily_news,
        trigger="cron",
        hour=config.news_hour,
        minute=config.news_minute,
        args=[bot],
        id="daily_ai_news",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("스케줄러 시작 — 매일 %02d:%02d (KST) AI 뉴스 전송", config.news_hour, config.news_minute)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
