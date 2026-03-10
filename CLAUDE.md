# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Agent is a Telegram bot that acts as an AI-powered home server assistant. Users send natural language messages via Telegram, which are forwarded to Claude Code CLI for execution, with responses streamed back. The bot also delivers daily AI news digests via RSS feeds.

- **Language**: Python 3.12
- **Primary framework**: aiogram 3.x (async Telegram bot framework)
- **Database**: PostgreSQL via asyncpg (stores conversation history)
- **Scheduling**: APScheduler (daily news delivery)
- **Interface to Claude**: Shells out to `claude` CLI with `--dangerously-skip-permissions` flag

## Commands

```bash
# Activate virtualenv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m bot.main

# Run the bot via tmux wrapper (production)
./start.sh

# Run tests
python -m pytest tests/

# Run a single test
python -m pytest tests/test_claude_service.py
```

## Architecture

```
bot/
├── main.py              # Entry point: sets up Bot, Dispatcher, middleware, routers, scheduler
├── config.py            # Singleton Config dataclass, reads all settings from env vars
├── middleware/
│   └── auth.py          # AuthMiddleware: blocks non-whitelisted users (ALLOWED_USERS)
├── handlers/
│   ├── command.py       # /start, /help, /clear, /news command handlers
│   └── message.py       # Catch-all text handler: streams Claude CLI responses with typing indicator
├── services/
│   ├── claude.py        # Spawns `claude` CLI as subprocess, streams stdout chunks back
│   ├── memory.py        # PostgreSQL conversation store (save/get/clear context)
│   ├── news.py          # Fetches AI news from RSS feeds, deduplicates, formats
│   └── scheduler.py     # APScheduler cron job for daily news broadcast
└── utils/
    └── formatter.py     # Splits long text into Telegram-safe 4096-char chunks
```

### Key Data Flow

1. Telegram message → AuthMiddleware (user whitelist check) → command router or message router
2. Message handler retrieves last N conversation turns from PostgreSQL (`memory.get_context`)
3. `claude.ask_claude_stream` builds a prompt with conversation context and spawns `claude` CLI
4. Stdout is read in 256-byte chunks and flushed to Telegram every 3 seconds
5. Full response is saved back to PostgreSQL for future context

### Configuration

All config is via environment variables (see `.env.example`). Key settings:
- `CLAUDE_CHUNK_TIMEOUT` (default 300s) / `CLAUDE_TOTAL_TIMEOUT` (default 600s) / `CLAUDE_MAX_TURNS`: Control Claude CLI execution limits
- `CLAUDE_CWD`: Working directory for Claude CLI subprocess (defaults to home dir)
- `MEMORY_CONTEXT_COUNT`: Number of recent messages included as conversation context (default 20)
- `NEWS_HOUR` / `NEWS_MINUTE`: Daily news delivery time in KST

### Notes

- The bot runs as a systemd service (`home-agent.service`) or in a tmux session (`start.sh`)
- The `CLAUDECODE` env var is explicitly stripped when spawning the Claude CLI subprocess to avoid conflicts
- The UI language is Korean (user-facing messages, logs, comments)
