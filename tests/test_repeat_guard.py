"""重复动作 Guard 测试(移植自 miniMaster test_guard.py + SafetyGuard 集成)。"""
from __future__ import annotations

from agentmuster.safety import RepeatedActionGuard
from agentmuster.state import TaskInput


def test_repeated_action_blocked_after_limit():
    guard = RepeatedActionGuard(max_repeat=2)
    args = {"command": "ls"}
    assert guard.check("bash", args).allowed
    assert guard.check("bash", args).allowed
    verdict = guard.check("bash", args)  # 第 3 次连续重复 → 拦截
    assert not verdict.allowed
    assert verdict.repeat_count == 3
    assert verdict.rule == "consecutive"
    assert verdict.message is not None and "更换策略" in verdict.message


def test_different_action_resets_counter():
    guard = RepeatedActionGuard(max_repeat=2)
    guard.check("bash", {"command": "ls"})
    guard.check("bash", {"command": "ls"})
    verdict = guard.check("read", {"path": "a.txt"})
    assert verdict.allowed
    assert verdict.repeat_count == 1


def test_arg_change_is_not_repeat():
    guard = RepeatedActionGuard(max_repeat=2)
    guard.check("bash", {"command": "ls"})
    assert guard.check("bash", {"command": "ls -la"}).allowed


def test_reset_between_tasks():
    guard = RepeatedActionGuard(max_repeat=1)
    guard.check("bash", {"command": "ls"})
    guard.check("bash", {"command": "ls"})
    guard.reset()
    assert guard.check("bash", {"command": "ls"}).allowed


def test_alternating_cycle_blocked():
    # A→B→A→B 振荡:第 4 次动作触发周期检测(连续重复规则已不适用)
    guard = RepeatedActionGuard(max_repeat=2)
    assert guard.check("bash", {"command": "ls"}).allowed      # A
    assert guard.check("read", {"path": "a"}).allowed          # B
    assert guard.check("bash", {"command": "ls"}).allowed      # A(连续=1)
    verdict = guard.check("read", {"path": "a"})               # B → A,B,A,B 循环
    assert not verdict.allowed
    assert verdict.rule == "cycle"


def test_high_frequency_in_window_blocked():
    # 非连续、非严格周期,但窗口内同动作高频复现
    guard = RepeatedActionGuard(max_repeat=2, window_size=12, window_max=4)
    seq = [
        ("bash", {"command": "ls"}),
        ("read", {"path": "a"}),
        ("write", {"path": "b"}),
        ("bash", {"command": "ls"}),
        ("read", {"path": "a"}),
        ("glob", {"pattern": "*"}),
        ("bash", {"command": "ls"}),
        ("grep", {"pattern": "x"}),
    ]
    verdict = None
    for action, args in seq:
        verdict = guard.check(action, args)
    assert verdict is not None and verdict.allowed  # 前 8 步各动作 ≤3 次
    verdict = guard.check("bash", {"command": "ls"})  # 第 4 次 → 窗口规则
    assert not verdict.allowed
    assert verdict.rule == "window"


# ---- SafetyGuard 检查链集成 ----

def test_guard_blocks_third_identical_call(make_harness):
    # 同一工具+参数第 3 次连续调用被 Guard 拦截(去重缓存命中也计入指纹)
    script = [
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"content": "已了解内容,结束"},
    ]
    harness = make_harness(script=script)
    harness.workspace.write_text("a.txt", "内容")
    result = harness.run(TaskInput(task_id="t-guard", goal="读文件"))
    assert result.status == "completed"
    assert harness.guard.denied >= 1  # 第 3 次被拦截并计数
    assert harness.guard.repeat_guard is not None


def test_guard_disabled_by_config(make_harness):
    script = [
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"tool_calls": [{"name": "file_read", "arguments": {"path": "a.txt"}}]},
        {"content": "结束"},
    ]
    harness = make_harness(script=script, **{"safety.repeat_guard.enabled": False})
    harness.workspace.write_text("a.txt", "内容")
    result = harness.run(TaskInput(task_id="t-noguard", goal="读文件"))
    assert result.status == "completed"
    assert harness.guard.repeat_guard is None  # 整体关闭,靠去重缓存兜底
    assert harness.guard.denied == 0
