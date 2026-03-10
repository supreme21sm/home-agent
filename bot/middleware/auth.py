import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.config import config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """허용된 사용자만 봇을 사용할 수 있도록 필터링한다."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if event.from_user else None

        if user_id not in config.allowed_users:
            logger.warning("인증 거부: user_id=%s", user_id)
            await event.answer("⛔ 접근 권한이 없습니다.")
            return None

        return await handler(event, data)
