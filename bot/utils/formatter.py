"""Claude 응답을 Telegram 메시지 형식으로 변환한다."""

# Telegram 메시지 최대 길이
MAX_MESSAGE_LENGTH = 4096


def split_message(text: str) -> list[str]:
    """긴 텍스트를 Telegram 메시지 최대 길이에 맞게 분할한다."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            chunks.append(text)
            break

        # 코드 블록 안에서 자르지 않도록 최대한 줄바꿈에서 자른다
        cut = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if cut <= 0:
            cut = MAX_MESSAGE_LENGTH

        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")

    return chunks
