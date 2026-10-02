"""结构化输出助手测试(util.extract_json + structured_complete 反馈重试环)。"""
from __future__ import annotations

import pytest

from agentmuster.models import MockBackend
from agentmuster.models.base import ModelBackend, ModelResponse
from agentmuster.orchestrator.structured import StructuredOutputError, structured_complete
from agentmuster.state import Message
from agentmuster.util import extract_json


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('说明文字\n```json\n{"a": 1}\n```\n后缀') == {"a": 1}
    assert extract_json('前缀 {"a": {"b": 2}} 后缀') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        extract_json("不是 JSON")
    with pytest.raises(ValueError):
        extract_json("")


def test_structured_first_try():
    backend = MockBackend(script=[{"content": '{"ok": true}'}])
    assert structured_complete(backend, [Message("user", "go")]) == {"ok": True}


def test_structured_feedback_retry():
    # 第一次输出非 JSON → 反馈回灌 → 第二次成功
    backend = MockBackend(script=[{"content": "我觉得没法输出"},
                                  {"content": '{"ok": 1}'}])
    assert structured_complete(backend, [Message("user", "go")]) == {"ok": 1}


def test_structured_exhausted_raises():
    backend = MockBackend(script=[{"content": "坏输出"}] * 3)
    with pytest.raises(StructuredOutputError):
        structured_complete(backend, [Message("user", "go")], max_attempts=3)


def test_structured_truncated_feedback():
    class _TruncThenGood(ModelBackend):
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages, tools=None, temperature=0.0):
            self.calls += 1
            if self.calls == 1:
                return ModelResponse(content='{"a":', finish_reason="length")
            return ModelResponse(content='{"a": 1}', finish_reason="stop")

    backend = _TruncThenGood()
    assert structured_complete(backend, [Message("user", "go")]) == {"a": 1}
    assert backend.calls == 2  # 截断后触发了一次反馈重问
