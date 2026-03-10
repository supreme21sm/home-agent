import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    telegram_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_TOKEN", ""))
    allowed_users: list[int] = field(default_factory=lambda: [
        int(uid.strip())
        for uid in os.environ.get("ALLOWED_USERS", "").split(",")
        if uid.strip()
    ])

    # PostgreSQL
    pg_host: str = field(default_factory=lambda: os.environ.get("POSTGRES_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.environ.get("POSTGRES_PORT", "5432")))
    pg_user: str = field(default_factory=lambda: os.environ.get("POSTGRES_USER", "seongmin"))
    pg_password: str = field(default_factory=lambda: os.environ.get("POSTGRES_PASSWORD", ""))
    pg_db: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB", "claude_memory"))

    # Claude Code CLI
    claude_chunk_timeout: int = field(default_factory=lambda: int(os.environ.get("CLAUDE_CHUNK_TIMEOUT", "300")))
    claude_total_timeout: int = field(default_factory=lambda: int(os.environ.get("CLAUDE_TOTAL_TIMEOUT", "600")))
    claude_max_turns: int = field(default_factory=lambda: int(os.environ.get("CLAUDE_MAX_TURNS", "10")))
    claude_cwd: str = field(default_factory=lambda: os.environ.get("CLAUDE_CWD", "/home/seongmin-choi"))

    # Memory
    memory_context_count: int = field(default_factory=lambda: int(os.environ.get("MEMORY_CONTEXT_COUNT", "20")))

    # News
    news_hour: int = field(default_factory=lambda: int(os.environ.get("NEWS_HOUR", "9")))
    news_minute: int = field(default_factory=lambda: int(os.environ.get("NEWS_MINUTE", "0")))


config = Config()
