import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.memory import clear_context
from bot.services.news import fetch_news_by_category, format_news, NEWS_CATEGORIES

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🏠 홈서버 AI 에이전트입니다.\n\n"
        "메시지를 보내면 Claude가 홈서버를 제어하여 답변합니다.\n\n"
        "명령어:\n"
        "/help - 도움말\n"
        "/clear - 대화 기록 초기화\n"
        "/news - AI 뉴스 보기"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 사용 가이드\n\n"
        "자연어로 홈서버 관련 질문이나 명령을 보내세요.\n\n"
        "예시:\n"
        "• 디스크 용량 확인해줘\n"
        "• Docker 컨테이너 상태 보여줘\n"
        "• MySQL에서 최근 로그 조회해줘\n"
        "• nginx 설정 파일 확인해줘\n\n"
        "명령어:\n"
        "/clear - 대화 기록 초기화\n"
        "/help - 이 도움말"
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    user_id = message.from_user.id
    count = await clear_context(user_id)
    await message.answer(f"🗑️ 대화 기록 {count}건을 삭제했습니다.")
    logger.info("사용자 %d 대화 초기화 (%d건)", user_id, count)


@router.message(Command("news"))
async def cmd_news(message: Message) -> None:
    await message.answer("📡 뉴스를 수집 중입니다 (AI/정치/경제/사회)...")
    for category in NEWS_CATEGORIES:
        items = await fetch_news_by_category(category)
        text = format_news(items, category)
        await message.answer(text, disable_web_page_preview=True)
