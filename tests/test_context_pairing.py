"""上下文裁剪的 tool_calls 配对不变量回归(批次③,D9)。

取自 miniMaster LiveContextTrimmer 的核心保障(该组件按 D9 不移植,但其
"裁剪不得破坏协议配对"的不变量以回归测试形式固化于此):ContextManager 以
「轮」为粒度折叠/丢弃历史(assistant+tool 原子成组),配对应天然保持;
本文件防止未来裁剪策略(按条消息裁剪等)破坏配对。
"""
from __future__ import annotations

from agentmuster.config import Config
from agentmuster.context import ContextManager
from agentmuster.state import Message


def _make_manager(hard_limit: int) -> ContextManager:
    cfg = Config()
    cfg.set("context.hard_limit_tokens", hard_limit)
    return ContextManager(cfg)


def _assert_paired(messages: list[Message]) -> None:
    call_ids = {tc.get("id") for m in messages if m.tool_calls
                for tc in (m.tool_calls or [])}
    tool_ids = {m.tool_call_id for m in messages if m.role == "tool"}
    call_ids.discard(None)
    tool_ids.discard(None)
    assert call_ids == tool_ids, f"配对破坏: calls={call_ids} tools={tool_ids}"
    for idx, m in enumerate(messages):
        if m.role == "tool":
            owners = [x for x in messages[:idx] if x.tool_calls
                      and any(tc.get("id") == m.tool_call_id for tc in (x.tool_calls or []))]
            assert owners, f"tool 消息 {m.tool_call_id} 缺少发起方 assistant"


def test_prune_preserves_tool_call_pairing():
    cm = _make_manager(hard_limit=80)
    cm.set_task("读文件并总结", [], "")
    for i in range(10):
        cm.append_turn(
            Message("assistant", "", tool_calls=[{"id": f"c{i}", "name": "file_read",
                                                  "arguments": f'{{"path": "f{i}.txt"}}'}]),
            [Message("tool", f"文件{i}内容" * 30, name="file_read", tool_call_id=f"c{i}")])
    msgs = cm.assemble()
    _assert_paired(msgs)
    assert len(msgs) < 30  # 确实发生了裁剪


def test_no_prune_keeps_everything_paired():
    cm = _make_manager(hard_limit=100000)
    cm.set_task("小任务", [], "")
    for i in range(3):
        cm.append_turn(
            Message("assistant", "", tool_calls=[{"id": f"c{i}", "name": "file_read",
                                                  "arguments": "{}"}]),
            [Message("tool", "内容", name="file_read", tool_call_id=f"c{i}")])
    msgs = cm.assemble()
    _assert_paired(msgs)
    assert sum(1 for m in msgs if m.role == "tool") == 3
