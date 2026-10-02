"""编排层角色视图记忆(移植自 miniMaster,按设计 D8 拆解)。

子任务内部的执行轨迹由各 AgentHarness 的上下文治理与结构化记忆负责,不再
进入编排层;本模块只保留两个角色视图的渲染与一个任务级活动日志:

  * Planner 视图:只看任务状态与结论(不看原始工具输出),供 replan 定位;
  * Validator 视图:Checklist + 各任务执行结论,供逐项判定;
  * 活动日志:有界队列 + 读写锁(并行子任务下线程安全),供 replan 上下文
    与 orchestration 工件导出。
"""
from __future__ import annotations

import threading
from collections import deque

from ..util import truncate
from .checklist import CompletionChecklist
from .tasks import Task


def render_planner_view(tasks: list[Task]) -> str:
    """Planner 视图:任务全量渲染(状态/依赖/结论)。"""
    return "\n\n".join(t.render() for t in tasks)


def render_validator_view(checklist: CompletionChecklist, tasks: list[Task]) -> str:
    """Validator 视图:Checklist + 各任务执行结论。"""
    lines = [checklist.render(), "", "各任务执行结论:"]
    for t in tasks:
        summary = t.result_summary or "(未执行)"
        lines.append(f"- [{t.id}] ({t.status.value}, 尝试{t.attempts}次) {t.title} → {summary}")
    return "\n".join(lines)


class WorkingMemory:
    """任务级活动日志:有界队列 + 读写锁。"""

    def __init__(self, activity_maxlen: int = 50, detail_max_chars: int = 2000) -> None:
        self._activity: deque[dict] = deque(maxlen=activity_maxlen)
        self._lock = threading.Lock()
        self._detail_max_chars = detail_max_chars

    def add_task_event(self, task_id: str, action: str, detail: str = "") -> None:
        record = {"task_id": task_id, "action": action,
                  "detail": truncate(detail, self._detail_max_chars)}
        with self._lock:
            self._activity.append(record)

    def recent_activity(self, n: int | None = None) -> list[str]:
        """最近 n 条活动渲染行;None = 全部(受 maxlen 上界约束)。"""
        with self._lock:
            records = list(self._activity)
        if n is not None:
            records = records[-n:]
        return [f"[{r['task_id']}] {r['action']}: {r['detail']}" for r in records]

    def all_activity(self) -> list[dict]:
        with self._lock:
            return list(self._activity)
