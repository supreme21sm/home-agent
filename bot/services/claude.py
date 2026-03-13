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
        leftover = b""  # 잘린 멀티바이트 문자 버퍼

        while True:
            data = await proc.stdout.read(CHUNK_SIZE)

            if not data:
                # 남은 버퍼 처리
                if leftover:
                    yield leftover.decode("utf-8", errors="replace")
                break

            data = leftover + data
            # 끝에서 잘린 멀티바이트 문자가 있는지 확인
            # UTF-8 continuation byte(0x80-0xBF)로 끝나는 불완전 시퀀스 처리
            cut = 0
            if data and data[-1] & 0x80:  # 마지막 바이트가 ASCII가 아닌 경우
                # 뒤에서부터 시작 바이트를 찾아 완전한 문자인지 확인
                for i in range(min(4, len(data)), 0, -1):
                    byte = data[-i]
                    if byte & 0xC0 != 0x80:  # 시작 바이트 발견
                        if byte & 0xE0 == 0xC0:
                            expected = 2
                        elif byte & 0xF0 == 0xE0:
                            expected = 3
                        elif byte & 0xF8 == 0xF0:
                            expected = 4
                        else:
                            expected = 1
                        if i < expected:  # 불완전한 시퀀스
                            cut = i
                        break

            if cut:
                leftover = data[-cut:]
                data = data[:-cut]
            else:
                leftover = b""

            if data:
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
