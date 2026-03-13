import asyncio
import logging

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.types import Message

from bot.services.claude import ask_claude_stream
from bot.services.memory import get_context, save_message
from bot.utils.formatter import split_message

logger = logging.getLogger(__name__)
router = Router(name="messages")


async def _keep_typing(bot: Bot, chat_id: int, stop: asyncio.Event) -> None:
    """응답이 올 때까지 5초마다 타이핑 표시를 보낸다."""
    while not stop.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=5)
            break
        except asyncio.TimeoutError:
            pass


@router.message()
async def handle_message(message: Message, bot: Bot) -> None:
    """일반 텍스트 메시지를 Claude에 전달하고 완성된 응답을 한 번에 보낸다."""
    text = message.text
    if not text:
        return

    user_id = message.from_user.id
    logger.info("메시지 수신: user=%d, text=%s", user_id, text[:80])

    # 타이핑 표시 시작
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(bot, message.chat.id, stop_typing))

    try:
        # 대화 컨텍스트 조회
        context = await get_context(user_id)

        # 사용자 메시지 저장
        await save_message(user_id, "user", text)

        # Claude 호출 — 전체 응답을 모은 후 한 번에 전송
        chunks = []
        async for chunk in ask_claude_stream(text, conversation_context=context):
            chunks.append(chunk)

        response = "".join(chunks)

        if response:
            for part in split_message(response):
                try:
                    await message.reply(part, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    # Markdown 파싱 실패 시 plain text로 전송
                    await message.reply(part)

            await save_message(user_id, "assistant", response)

        logger.info("응답 전송 완료: user=%d, len=%d", user_id, len(response))
    finally:
        stop_typing.set()
        await typing_task
