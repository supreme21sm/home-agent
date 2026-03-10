import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import config
from bot.handlers import command, message
from bot.middleware.auth import AuthMiddleware
from bot.services.memory import close_db, init_db
from bot.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Home Agent 시작")
    logger.info("허용 사용자: %s", config.allowed_users)

    # DB 초기화
    await init_db()

    bot = Bot(token=config.telegram_token)
    dp = Dispatcher()

    # 인증 미들웨어 등록
    dp.message.middleware(AuthMiddleware())

    # 라우터 등록 (command가 먼저 매칭되도록)
    dp.include_router(command.router)
    dp.include_router(message.router)

    async def on_startup() -> None:
        start_scheduler(bot)
        for user_id in config.allowed_users:
            try:
                await bot.send_message(user_id, "✅ 봇이 재시작되었습니다.")
            except Exception as e:
                logger.warning("시작 알림 전송 실패 (user_id=%s): %s", user_id, e)

    dp.startup.register(on_startup)

    try:
        logger.info("Long Polling 시작...")
        await dp.start_polling(bot)
    finally:
        stop_scheduler()
        await close_db()
        await bot.session.close()
        logger.info("Home Agent 종료")


if __name__ == "__main__":
    asyncio.run(main())
