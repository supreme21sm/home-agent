import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from bot.config import config

logger = logging.getLogger(__name__)

CHUNK_SIZE = 256  # stdout에서 한 번에 읽는 바이트 수


async def ask_claude_stream(
    message: str,
    conversation_context: list[dict] | None = None,
    cwd: str | None = None,
) -> AsyncGenerator[str, None]:
    """Claude Code CLI를 호출하여 텍스트를 실시간으로 yield한다.

    plain text 출력을 stdout에서 chunk 단위로 읽어 스트리밍한다.
    """
    cwd = cwd or config.claude_cwd
    prompt = _build_prompt(message, conversation_context)

    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "text",
        "--max-turns", str(config.claude_max_turns),
        "--dangerously-skip-permissions",
    ]

    logger.info("Claude CLI 스트리밍 호출: %s (cwd=%s)", message[:80], cwd)

    proc = None
    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        has_output = False

        while True:
            try:
                data = await asyncio.wait_for(
                    proc.stdout.read(CHUNK_SIZE),
                    timeout=config.claude_timeout,
                )
            except asyncio.TimeoutError:
                logger.error("Claude CLI 스트리밍 타임아웃 (%ds)", config.claude_timeout)
                proc.kill()
                yield f"⚠️ 응답 시간 초과 ({config.claude_timeout}초)"
                return

            if not data:
                break

            text = data.decode("utf-8", errors="replace")
            if text:
                has_output = True
                yield text

        await proc.wait()

        if not has_output:
            stderr_output = await proc.stderr.read()
            err = stderr_output.decode().strip()
            if err:
                logger.error("Claude CLI stderr: %s", err)
                yield f"⚠️ Claude 오류: {err}"
            else:
                yield "응답을 받지 못했습니다. 다시 질문해주세요."

    except FileNotFoundError:
        logger.error("Claude CLI를 찾을 수 없습니다")
        yield "⚠️ Claude Code CLI가 설치되지 않았습니다."
    except Exception as e:
        logger.exception("Claude CLI 스트리밍 중 예외 발생")
        yield f"⚠️ 오류 발생: {e}"
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass


async def ask_claude(
    message: str,
    conversation_context: list[dict] | None = None,
    cwd: str | None = None,
) -> str:
    """Claude Code CLI를 호출하여 전체 응답을 받는다 (호환용)."""
    parts = []
    async for chunk in ask_claude_stream(message, conversation_context, cwd):
        parts.append(chunk)
    return "".join(parts)


def _build_prompt(message: str, context: list[dict] | None) -> str:
    """대화 컨텍스트를 포함한 프롬프트를 구성한다."""
    if not context:
        return message

    lines = ["[이전 대화 기록]"]
    for msg in context:
        role = "사용자" if msg["role"] == "user" else "어시스턴트"
        lines.append(f"{role}: {msg['content']}")
    lines.append("")
    lines.append(f"[현재 질문]\n{message}")
    return "\n".join(lines)
