import pytest

from bot.services.claude import _build_prompt


class TestBuildPrompt:
    def test_no_context(self):
        result = _build_prompt("안녕", None)
        assert result == "안녕"

    def test_empty_context(self):
        result = _build_prompt("안녕", [])
        assert result == "안녕"

    def test_with_context(self):
        context = [
            {"role": "user", "content": "디스크 확인해줘"},
            {"role": "assistant", "content": "df -h 결과입니다..."},
        ]
        result = _build_prompt("더 자세히", context)
        assert "[이전 대화 기록]" in result
        assert "사용자: 디스크 확인해줘" in result
        assert "어시스턴트: df -h 결과입니다..." in result
        assert "[현재 질문]\n더 자세히" in result
