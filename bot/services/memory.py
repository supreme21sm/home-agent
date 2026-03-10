import logging
from datetime import datetime, timezone

import asyncpg

from bot.config import config

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

INIT_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id
    ON conversations (user_id, created_at DESC);
"""


async def init_db() -> None:
    """DB 연결 풀을 생성하고 테이블을 초기화한다."""
    global _pool
    _pool = await asyncpg.create_pool(
        host=config.pg_host,
        port=config.pg_port,
        user=config.pg_user,
        password=config.pg_password,
        database=config.pg_db,
        min_size=1,
        max_size=5,
    )
    async with _pool.acquire() as conn:
        await conn.execute(INIT_SQL)
    logger.info("DB 초기화 완료")


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def save_message(user_id: int, role: str, content: str) -> None:
    """대화 메시지를 저장한다."""
    if not _pool:
        return
    await _pool.execute(
        "INSERT INTO conversations (user_id, role, content, created_at) VALUES ($1, $2, $3, $4)",
        user_id, role, content, datetime.now(timezone.utc),
    )


async def get_context(user_id: int) -> list[dict]:
    """최근 N개의 대화 메시지를 조회한다."""
    if not _pool:
        return []
    rows = await _pool.fetch(
        """
        SELECT role, content FROM conversations
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id, config.memory_context_count,
    )
    # 최신순 → 시간순으로 뒤집기
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def clear_context(user_id: int) -> int:
    """사용자의 대화 기록을 삭제한다. 삭제된 행 수를 반환."""
    if not _pool:
        return 0
    result = await _pool.execute(
        "DELETE FROM conversations WHERE user_id = $1", user_id,
    )
    # "DELETE 42" 형식에서 숫자 추출
    count = int(result.split()[-1])
    logger.info("사용자 %d 대화 기록 %d건 삭제", user_id, count)
    return count
