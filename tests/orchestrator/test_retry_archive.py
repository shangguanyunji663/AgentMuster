"""Retry Archive 测试(移植自 miniMaster 相关用例)。"""
from __future__ import annotations

from agentmuster.orchestrator.retry_archive import RetryArchive, RetryRecord
from agentmuster.orchestrator.tasks import Task


def test_archive_truncate_fallback():
    t = Task("T1", "标题")
    t.attempts = 1
    arch = RetryArchive()  # 未注入 compress_fn → 确定性截断
    rec = arch.archive(t, "失败原因" * 1000)
    assert rec.attempt == 1 and len(rec.lessons) <= 2500 and len(rec.failure_reason) <= 1500
    assert arch.for_task("T1") == [rec]


def test_archive_with_compress_fn():
    t = Task("T1", "标题")
    t.attempts = 2
    arch = RetryArchive(compress_fn=lambda title, attempt, failure: f"教训({title},{attempt})")
    rec = arch.archive(t, "原因")
    assert rec.lessons == "教训(标题,2)"  # compress_fn 收到的是任务标题
    assert "第 2 次尝试失败" in arch.render_for_task("T1")
    assert arch.render_for_task("T9") == ""


def test_restore_and_all_records():
    arch = RetryArchive()
    arch.restore([RetryRecord("T1", "标题", 1, "原因", "教训")])
    assert len(arch.all_records()) == 1
    assert arch.for_task("T1")[0].lessons == "教训"


def test_multiple_failures_appended():
    arch = RetryArchive(compress_fn=lambda title, attempt, failure: f"L{attempt}")
    for attempt in (1, 2):
        t = Task("T1", "标题")
        t.attempts = attempt
        arch.archive(t, "原因")
    assert [r.lessons for r in arch.for_task("T1")] == ["L1", "L2"]
