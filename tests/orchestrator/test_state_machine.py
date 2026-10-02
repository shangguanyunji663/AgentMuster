"""任务状态机测试(移植自 miniMaster test_state_machine.py)。"""
from __future__ import annotations

import pytest

from agentmuster.orchestrator.tasks import ALLOWED_TRANSITIONS, IllegalTransitionError, Task, TaskStatus


def test_legal_transitions():
    t = Task("T1", "标题", "描述", "标准")
    assert t.status is TaskStatus.PENDING
    t.transition(TaskStatus.RUNNING)
    assert t.attempts == 1  # 进入 RUNNING 计一次尝试
    t.transition(TaskStatus.DONE)
    assert t.is_terminal


def test_retry_reentry():
    t = Task("T1", "标题")
    t.transition(TaskStatus.RUNNING)
    t.transition(TaskStatus.FAILED)
    t.transition(TaskStatus.PENDING)  # 有重试额度时归档重注入
    t.transition(TaskStatus.RUNNING)
    assert t.attempts == 2


def test_blocked_transitions():
    t = Task("T1", "标题")
    t.transition(TaskStatus.BLOCKED)  # PENDING → BLOCKED(依赖未满足/预算耗尽)
    t.transition(TaskStatus.RUNNING)  # BLOCKED → RUNNING(绕行重跑)


def test_illegal_transitions_raise():
    t = Task("T1", "标题")
    with pytest.raises(IllegalTransitionError):
        t.transition(TaskStatus.DONE)  # PENDING → DONE 非法
    t.transition(TaskStatus.RUNNING)
    t.transition(TaskStatus.DONE)
    with pytest.raises(IllegalTransitionError):
        t.transition(TaskStatus.RUNNING)  # DONE 是终态,无出边
    # 错误信息应包含迁移路径与允许项
    t2 = Task("T2", "标题")
    with pytest.raises(IllegalTransitionError, match="PENDING"):
        t2.transition(TaskStatus.DONE)


def test_transition_table_shape():
    assert ALLOWED_TRANSITIONS[TaskStatus.DONE] == set()
    assert TaskStatus.PENDING in ALLOWED_TRANSITIONS[TaskStatus.FAILED]
    assert {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.BLOCKED} \
        == ALLOWED_TRANSITIONS[TaskStatus.RUNNING]


def test_dict_roundtrip():
    t = Task("T1", "标题", "描述", "标准", depends_on=["T0"])
    t.transition(TaskStatus.RUNNING)
    t.result_summary = "结论"
    t2 = Task.from_dict(t.to_dict())
    assert t2.id == "T1" and t2.status is TaskStatus.RUNNING and t2.attempts == 1
    assert t2.depends_on == ["T0"] and t2.result_summary == "结论"


def test_self_dependency_stored_as_is():
    """自依赖由编排层 sanitize 剔除,状态机本身不越权改数据。"""
    t = Task("T1", "标题", depends_on=["T1"])
    assert t.depends_on == ["T1"]


def test_render_contains_fields():
    t = Task("T1", "标题", "描述", "标准", depends_on=["T0"])
    t.result_summary = "结论"
    text = t.render()
    assert "[T1]" in text and "依赖: T0" in text and "完成标准" in text and "结论" in text
