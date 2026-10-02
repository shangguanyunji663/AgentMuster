"""Validator 角色:对照 Completion Checklist 验收,产出精确的 missing_requirements。

移植自 miniMaster(agents/validator.py,快照 24f4247):判定结果写回 Checklist
(satisfied + evidence),未满足项回流 Harness 反馈闭环,驱动下一轮精确修复。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..agent.prompts import role_system_message
from ..models.base import ModelBackend
from ..state import Message
from .checklist import CompletionChecklist
from .structured import structured_complete
from .tasks import Task
from .working_memory import render_validator_view

EmitFn = Callable[[dict], None]


@dataclass
class ValidationVerdict:
    completed: bool
    missing_requirements: list[str] = field(default_factory=list)
    summary: str = ""


class ValidatorRole:
    role = "VALIDATOR"

    def __init__(self, backend: ModelBackend, on_event: EmitFn | None = None,
                 temperature: float = 0.0) -> None:
        self.backend = backend
        self.on_event = on_event
        self.temperature = temperature

    def _emit(self, event: dict) -> None:
        if self.on_event is not None:
            self.on_event(event)

    def verify(self, goal: str, checklist: CompletionChecklist,
               tasks: list[Task]) -> ValidationVerdict:
        view = render_validator_view(checklist, tasks)
        messages = [
            Message("system", role_system_message("validator",
                                                  {"goal": goal, "validator_view": view})),
            Message("user", "请对照 Completion Checklist 逐项判定,输出 JSON 判定结果。"),
        ]
        data = structured_complete(self.backend, messages, temperature=self.temperature)

        updates = data.get("items") or []
        checklist.apply_verdict(updates if isinstance(updates, list) else [])
        missing = [
            str(m) for m in (data.get("missing_requirements") or []) if str(m).strip()
        ]
        if not checklist.is_complete:
            missing += [
                f"Checklist 未满足: {item.text}"
                for item in checklist.unmet()
                if all(item.text != str(m).strip() for m in missing)
            ]
        verdict = ValidationVerdict(
            completed=bool(data.get("completed")) and checklist.is_complete,
            missing_requirements=missing,
            summary=str(data.get("summary", "")),
        )
        self._emit({"type": "orchestration_validated",
                    "completed": verdict.completed,
                    "unmet_items": len(checklist.unmet()),
                    "missing": verdict.missing_requirements[:3],
                    "summary": verdict.summary[:200]})
        return verdict
