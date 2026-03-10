import pytest
import asyncpg

from bot.services import memory
from bot.config import config


@pytest.fixture
async def db():
    """테스트용 DB 연결을 설정하고 테스트 후 정리한다."""
    await memory.init_db()
    yield
    # 테스트 데이터 정리
    if memory._pool:
        await memory._pool.execute("DELETE FROM conversations WHERE user_id = 99999")
    await memory.close_db()


TEST_USER = 99999


@pytest.mark.asyncio
async def test_save_and_get_context(db):
    await memory.save_message(TEST_USER, "user", "안녕")
    await memory.save_message(TEST_USER, "assistant", "안녕하세요!")

    ctx = await memory.get_context(TEST_USER)
    assert len(ctx) == 2
    assert ctx[0]["role"] == "user"
    assert ctx[0]["content"] == "안녕"
    assert ctx[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_clear_context(db):
    await memory.save_message(TEST_USER, "user", "테스트")
    count = await memory.clear_context(TEST_USER)
    assert count >= 1

    ctx = await memory.get_context(TEST_USER)
    assert len(ctx) == 0
