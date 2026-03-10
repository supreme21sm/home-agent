import json
import pytest

from bot.services.claude import _build_prompt, _parse_stream_json


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


class TestParseStreamJson:
    def test_result_event(self):
        events = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "중간"}]}},
            {"type": "result", "result": "최종 결과"},
        ]
        output = "\n".join(json.dumps(e) for e in events)
        assert _parse_stream_json(output) == "최종 결과"

    def test_no_result_falls_back_to_assistant(self):
        events = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "파트1"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "파트2"}]}},
        ]
        output = "\n".join(json.dumps(e) for e in events)
        assert _parse_stream_json(output) == "파트1\n파트2"

    def test_empty_output(self):
        assert _parse_stream_json("") == "응답을 받지 못했습니다."

    def test_invalid_json_lines_skipped(self):
        output = "not json\n" + json.dumps({"type": "result", "result": "OK"})
        assert _parse_stream_json(output) == "OK"
