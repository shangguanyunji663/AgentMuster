"""结构化输出助手:后端无关的 JSON 结构化调用。

移植自 miniMaster llm/client.py 的 chat_structured(快照 24f4247),改为直接
面向 ModelBackend:解析失败或输出被截断时,把错误反馈回模型重问,最多
max_attempts 次。配合 util.extract_json 的逐级候选解析(裸 JSON/代码块/首尾
大括号),对小模型的非规范输出有较强容错。
"""
from __future__ import annotations

from ..models.base import ModelBackend
from ..state import Message
from ..util import extract_json


class StructuredOutputError(Exception):
    """结构化输出在多次重试后仍无法解析为 JSON 对象。"""


def structured_complete(backend: ModelBackend, messages: list[Message],
                        temperature: float = 0.0, max_attempts: int = 3) -> dict:
    """发起一次结构化调用,返回解析后的 dict;失败抛 StructuredOutputError。"""
    convo = list(messages)
    last_error = ""
    for _ in range(max_attempts):
        resp = backend.complete(convo, tools=None, temperature=temperature)
        content = resp.content or ""
        if resp.finish_reason == "length":
            feedback = "你的输出被 max_tokens 截断。请精简内容,重新只输出一个完整 JSON 对象。"
        else:
            try:
                data = extract_json(content)
                if isinstance(data, dict):
                    return data
                raise ValueError("顶层不是 JSON 对象")
            except ValueError as exc:
                feedback = (f"输出不是合法 JSON({exc})。"
                            "请重新只输出一个完整 JSON 对象,不要附加任何其他文字。")
        last_error = feedback
        convo.append(Message("assistant", content))
        convo.append(Message("user", feedback))
    raise StructuredOutputError(f"结构化输出在 {max_attempts} 次尝试后仍失败: {last_error}")
