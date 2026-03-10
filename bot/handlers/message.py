import asyncio
import logging
import time

from aiogram import Bot, Router
from aiogram.types import Message

from bot.services.claude import ask_claude_stream
from bot.services.memory import get_context, save_message
from bot.utils.formatter import split_message

logger = logging.getLogger(__name__)
router = Router(name="messages")

# 스트리밍 설정
FLUSH_INTERVAL = 3.0  # 초 단위: 이 간격마다 중간 메시지 전송
FLUSH_MIN_LENGTH = 50  # 최소 이 길이 이상 쌓여야 중간 전송


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
    """일반 텍스트 메시지를 Claude에 전달하고 스트리밍으로 응답한다."""
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

        # 스트리밍으로 Claude 호출
        full_response = []
        pending_buffer = []
        last_flush_time = time.monotonic()

        async for chunk in ask_claude_stream(text, conversation_context=context):
            full_response.append(chunk)
            pending_buffer.append(chunk)

            now = time.monotonic()
            pending_text = "".join(pending_buffer)

            # 일정 간격마다 중간 메시지 전송
            if (now - last_flush_time >= FLUSH_INTERVAL
                    and len(pending_text) >= FLUSH_MIN_LENGTH):
                for part in split_message(pending_text):
                    await message.answer(part)
                pending_buffer.clear()
                last_flush_time = now

        # 남은 텍스트 전송
        remaining = "".join(pending_buffer)
        if remaining:
            for part in split_message(remaining):
                await message.answer(part)

        # 전체 응답 저장
        response = "".join(full_response)
        if response:
            await save_message(user_id, "assistant", response)

        logger.info("응답 전송 완료: user=%d, len=%d", user_id, len(response))
    finally:
        stop_typing.set()
        await typing_task
