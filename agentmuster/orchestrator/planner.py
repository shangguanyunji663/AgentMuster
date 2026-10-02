"""Planner 角色:目标拆解 + Completion Checklist 生成 + 缺失项增量重规划。

移植自 miniMaster(agents/planner.py,快照 24f4247),模型调用改为后端无关的
structured_complete;动作白名单硬校验随批次②并入 SafetyGuard 检查链。
"""
from __future__ import annotations

from collections.abc import Callable

from ..agent.prompts import role_system_message
from ..models.base import ModelBackend
from ..state import Message
from .checklist import ChecklistItem, CompletionChecklist
from .structured import structured_complete
from .tasks import Task

EmitFn = Callable[[dict], None]


class PlannerRole:
    role = "PLANNER"

    def __init__(self, backend: ModelBackend, on_event: EmitFn | None = None,
                 temperature: float = 0.2) -> None:
        self.backend = backend
        self.on_event = on_event
        self.temperature = temperature

    def _emit(self, event: dict) -> None:
        if self.on_event is not None:
            self.on_event(event)

    # ---- 初次规划 ----
    def plan(self, goal: str) -> tuple[list[Task], CompletionChecklist]:
        messages = [
            Message("system", role_system_message("planner", {"goal": goal})),
            Message("user", f"目标:{goal}\n\n请拆解子任务并生成验收清单。"),
        ]
        data = structured_complete(self.backend, messages, temperature=self.temperature)
        tasks = self._parse_tasks(data.get("tasks") or [])
        if not tasks:
            # 语义级重问:合法 JSON 但无可执行子任务(如 tasks 为空),反馈后重试一次
            messages.append(Message(
                "user",
                "上次输出没有可执行的子任务(tasks 为空)。"
                "请重新输出:至少 1 个子任务,且每项带可观测的 done_criteria。",
            ))
            data = structured_complete(self.backend, messages, temperature=self.temperature)
            tasks = self._parse_tasks(data.get("tasks") or [])
        if not tasks:
            raise ValueError("Planner 两次尝试后仍未产出任何子任务")
        items = [
            ChecklistItem(item_id=f"C{i}", text=str(text).strip())
            for i, text in enumerate(data.get("checklist") or [], 1)
            if str(text).strip()
        ]
        if not items:
            # 兜底:checklist 缺失/为空时从各任务完成标准派生,避免验收永假死局
            items = [
                ChecklistItem(item_id=f"C{i}", text=f"任务 {t.id} 达成: {t.done_criteria or t.title}")
                for i, t in enumerate(tasks, 1)
            ]
        checklist = CompletionChecklist(goal=goal, items=items)
        self._emit({"type": "orchestration_plan",
                    "tasks": [f"{t.id}:{t.title}" for t in tasks],
                    "checklist_items": len(items)})
        return tasks, checklist

    # ---- 增量重规划(BLOCKED / 验收缺失时)----
    def replan(self, goal: str, tasks: list[Task], missing_feedback: list[str],
               activity: list[str] | None = None) -> list[Task]:
        if not missing_feedback:
            return []
        context = {
            "replan": True,
            "goal": goal,
            "planner_view": "\n\n".join(t.render() for t in tasks),
            "missing_feedback": missing_feedback[:8],
        }
        system = role_system_message("planner", context)
        if activity:
            system += "\n\n## 最近活动\n" + "\n".join(activity[-8:])
        messages = [
            Message("system", system),
            Message("user", "请针对上述未满足项做增量重规划:只补充真正必要的新任务,"
                            "或对已 BLOCKED 任务给出替代路径。若无必要新增任务,tasks 返回空数组。"),
        ]
        data = structured_complete(self.backend, messages, temperature=self.temperature)
        new_tasks = self._parse_tasks(data.get("tasks") or [], start_index=len(tasks))
        known = {t.id for t in tasks}
        new_tasks = [t for t in new_tasks if t.id not in known]  # 复用已有 id 的增量任务直接丢弃
        self._emit({"type": "orchestration_replan",
                    "analysis": str(data.get("analysis", ""))[:200],
                    "new_tasks": [t.id for t in new_tasks]})
        return new_tasks

    # ---- 内部 ----
    @staticmethod
    def _parse_tasks(raw_tasks: list, start_index: int = 0) -> list[Task]:
        tasks: list[Task] = []
        for i, raw in enumerate(raw_tasks, start_index + 1):
            if not isinstance(raw, dict) or not str(raw.get("title", "")).strip():
                continue
            task_id = str(raw.get("id") or f"T{i}").strip()
            depends_on = [
                str(d).strip()
                for d in (raw.get("depends_on") or [])
                if str(d).strip() and str(d).strip() != task_id
            ]
            tasks.append(
                Task(
                    task_id=task_id,
                    title=str(raw["title"]).strip(),
                    description=str(raw.get("description", "")).strip(),
                    done_criteria=str(raw.get("done_criteria", "")).strip(),
                    depends_on=depends_on,
                )
            )
        return tasks
