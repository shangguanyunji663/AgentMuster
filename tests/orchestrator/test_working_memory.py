"""编排层角色视图记忆测试(移植自 miniMaster test_memory.py 的视图与并发部分)。"""
from __future__ import annotations

import threading

from agentmuster.orchestrator.checklist import ChecklistItem, CompletionChecklist
from agentmuster.orchestrator.tasks import Task
from agentmuster.orchestrator.working_memory import WorkingMemory, render_planner_view, render_validator_view


def test_views_trim_by_role():
    tasks = [Task("T1", "标题", "描述", "标准")]
    tasks[0].result_summary = "结论"
    cl = CompletionChecklist(goal="目标", items=[ChecklistItem("C1", "项1")])
    planner_view = render_planner_view(tasks)
    validator_view = render_validator_view(cl, tasks)
    assert "[T1]" in planner_view and "结论" in planner_view
    assert "Completion Checklist" in validator_view and "尝试0次" in validator_view
    assert "结论" in validator_view


def test_activity_bounded_and_thread_safe():
    mem = WorkingMemory(activity_maxlen=10)

    def worker() -> None:
        for i in range(100):
            mem.add_task_event(f"T{i}", "action", "细节" * 5000)  # 超长细节必须被截断

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(mem.all_activity()) == 10  # 有界队列
    assert all(len(r["detail"]) < 3000 for r in mem.all_activity())  # 一级截断生效


def test_recent_activity_window():
    mem = WorkingMemory()
    for i in range(5):
        mem.add_task_event(f"T{i}", "action", f"第{i}条")
    lines = mem.recent_activity(2)
    assert len(lines) == 2 and "第4条" in lines[-1] and "第3条" in lines[0]
