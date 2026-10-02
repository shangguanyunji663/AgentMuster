"""控制工具测试:submit_result / request_block 收口语义(批次②)。"""
from __future__ import annotations

from agentmuster.state import TaskInput
from agentmuster.tools import build_registry
from agentmuster.tools.control_tools import CONTROL_TOOLS


def test_control_tools_not_in_default_registry():
    reg = build_registry()
    assert not reg.has("submit_result")
    assert not reg.has("request_block")
    assert frozenset({"submit_result", "request_block"}) == CONTROL_TOOLS


def test_submit_result_terminates_completed(make_harness):
    script = [
        {"tool_calls": [{"name": "file_write",
                         "arguments": {"path": "out.txt", "content": "数据"}}]},
        {"tool_calls": [{"name": "submit_result",
                         "arguments": {"success": True, "summary": "已写入 out.txt:数据"}}]},
    ]
    harness = make_harness(script=script)
    result = harness.run(TaskInput(task_id="t-submit", goal="写文件"))
    assert result.status == "completed"
    assert result.final_answer == "已写入 out.txt:数据"
    assert result.control == {"action": "submit_result", "success": True}


def test_submit_result_failure_signal(make_harness):
    script = [{"tool_calls": [{"name": "submit_result",
                               "arguments": {"success": False, "summary": "端点不可用"}}]}]
    harness = make_harness(script=script)
    result = harness.run(TaskInput(task_id="t-fail", goal="x"))
    assert result.status == "completed"  # 收口语义由 control 字段承载
    assert result.control == {"action": "submit_result", "success": False}
    assert result.final_answer == "端点不可用"


def test_request_block_blocked_status(make_harness):
    script = [{"tool_calls": [{"name": "request_block",
                               "arguments": {"reason": "缺少上游依赖"}}]}]
    harness = make_harness(script=script)
    result = harness.run(TaskInput(task_id="t-block", goal="x"))
    assert result.status == "blocked"  # 批次② 新增状态
    assert result.final_answer == "缺少上游依赖"
    assert result.control == {"action": "request_block"}


def test_allowed_tools_policy_denial(make_harness):
    # 白名单外的工具被 SafetyGuard 拦截,拒绝原因回灌后模型改道收口
    script = [
        {"tool_calls": [{"name": "grep_search", "arguments": {"pattern": "x"}}]},
        {"tool_calls": [{"name": "submit_result",
                         "arguments": {"success": True, "summary": "白名单受限,提前收口"}}]},
    ]
    harness = make_harness(script=script)
    harness.allowed_tools = {"file_read", "submit_result", "request_block"}
    result = harness.run(TaskInput(task_id="t-policy", goal="搜索"))
    assert result.status == "completed"
    assert harness.guard.denied >= 1  # grep_search 被白名单拦截
    assert result.control == {"action": "submit_result", "success": True}
