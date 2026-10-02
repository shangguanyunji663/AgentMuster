"""多智能体编排:Planner-Executor-Validator 多轮闭环(移植自 miniMaster 角色层)。

round 表示一个完整的「执行 → 验收 →(未过则)重规划」周期;失败任务在轮内
工作队列中即时重入队(重试与轮次解耦);依赖就绪的任务可并行执行。每个子
任务仍由完全隔离根的独立 AgentHarness 执行(工作区/记忆/断点/工件互不污染)。

四重纠错闭环:
  1. Completion Checklist 驱动的验收判定(Validator 角色);
  2. 步数上限强制收口(子任务 harness 内);
  3. Validator missing_requirements 精确回流 → Planner 增量重规划;
  4. Retry Archive:失败轨迹压缩归档,重试时注入执行上下文。

确定性退化:未启用 LLM planner(orchestrator.planner_mode=deterministic)时
单任务单轮、无 Validator,保持原有一次性编排语义(向后兼容)。全局 token
预算(orchestrator.max_total_tokens)超限时剩余 PENDING 任务整体转 BLOCKED。
每轮收口与任务收口写编排快照,支持 resume 断点续跑。
"""
from __future__ import annotations

import contextlib
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..agent.prompts import FAILURE_COMPRESS_PROMPT
from ..checkpoint import CheckpointStore
from ..config import Config
from ..models import create_backend
from ..orchestrator.checklist import ChecklistItem, CompletionChecklist
from ..orchestrator.planner import PlannerRole
from ..orchestrator.retry_archive import RetryArchive
from ..orchestrator.snapshot import load_snapshot, restore_state, save_snapshot, snapshot_to_dict
from ..orchestrator.tasks import Task, TaskStatus
from ..orchestrator.validator import ValidationVerdict, ValidatorRole
from ..orchestrator.working_memory import WorkingMemory
from ..state import Message, TaskInput
from ..tools.control_tools import CONTROL_TOOLS, RequestBlockTool, SubmitResultTool
from ..util import short_id, truncate

EventFn = Callable[[dict], None]
BackendFactory = Callable[[Task], object]


def _default_planner(goal: str) -> list[dict]:
    """确定性退化分解:未提供 LLM planner 时,把目标整体作为一个子任务。"""
    return [{"id": "sub-1", "goal": goal}]


class _LegacyPlannerAdapter:
    """把旧式 Callable[[str], list[dict]] planner 适配为角色 planner 接口。"""

    def __init__(self, fn: Callable[[str], list[dict]]) -> None:
        self._fn = fn

    def plan(self, goal: str) -> tuple[list[Task], CompletionChecklist]:
        raw = self._fn(goal)
        tasks: list[Task] = []
        for i, item in enumerate(raw, 1):
            entry = item if isinstance(item, dict) else {"goal": str(item)}
            task_id = str(entry.get("id") or f"sub-{i}")
            goal_text = str(entry.get("goal") or entry)
            tasks.append(Task(task_id=task_id, title=goal_text, description=goal_text,
                              done_criteria=goal_text))
        checklist = CompletionChecklist(
            goal=goal,
            items=[ChecklistItem(item_id=f"C{i}", text=f"任务 {t.id} 达成: {t.done_criteria}")
                   for i, t in enumerate(tasks, 1)],
        )
        return tasks, checklist

    def replan(self, goal: str, tasks: list[Task], missing_feedback: list[str],
               activity: list[str] | None = None) -> list[Task]:
        return []


class Orchestrator:
    """把目标分解为子任务,多轮「执行→验收→重规划」直到 Checklist 通过或预算耗尽。"""

    def __init__(self, config: Config, planner: object | None = None,
                 validator: ValidatorRole | None = None,
                 backend_factory: BackendFactory | None = None,
                 max_workers: int | None = None, on_event: EventFn | None = None) -> None:
        self.config = config
        self.backend_factory = backend_factory
        self.on_event = on_event
        self.max_workers = max(1, int(max_workers
                                      or config.get("orchestrator.parallel", 1)))
        self.max_rounds = int(config.get("orchestrator.max_rounds", 3))
        self.max_retries = int(config.get("orchestrator.max_retries", 2))
        self.max_total_tokens = int(config.get("orchestrator.max_total_tokens", 800000))
        self.memory = WorkingMemory()
        self.archive = RetryArchive(compress_fn=self._compress_failure)
        self._store = CheckpointStore(config.get("checkpoint.root", ".agentmuster/checkpoints"),
                                      enabled=bool(config.get("checkpoint.enabled", True)))
        # planner 解析:显式注入 > planner_mode=llm 构建 > 确定性退化
        if planner is None and str(config.get("orchestrator.planner_mode", "deterministic")) == "llm":
            planner = PlannerRole(self._role_backend("planner"), on_event,
                                  float(config.get("orchestrator.roles.planner.temperature", 0.2)))
        if planner is None:
            planner = _default_planner
        self.planner: PlannerRole | _LegacyPlannerAdapter = (
            planner if isinstance(planner, (PlannerRole, _LegacyPlannerAdapter))
            else _LegacyPlannerAdapter(planner))  # type: ignore[arg-type]
        if validator is None and isinstance(self.planner, PlannerRole):
            validator = ValidatorRole(self._role_backend("validator"), on_event,
                                      float(config.get("orchestrator.roles.validator.temperature", 0.0)))
        self.validator = validator
        # 运行期状态(resume 语义见 run)
        self._resumed_snapshot: dict | None = None
        self._task_id = ""
        self._goal = ""
        self._tasks: list[Task] = []
        self._checklist = CompletionChecklist(goal="")
        self._round_no = 0
        self._used_tokens = 0

    # ------------------------------------------------------------------
    def _role_backend(self, role: str):
        """按角色模型路由构建后端(roles.<role>.model 空 = 主配置后端)。"""
        cfg = Config(self.config.to_dict())
        model = str(self.config.get(f"orchestrator.roles.{role}.model", "") or "")
        if model:
            cfg.set("model.local_openai.model", model)
        return create_backend(cfg)

    def _compress_failure(self, title: str, attempt: int, failure: str) -> str:
        """失败轨迹压缩:llm 摘要模式用模型压缩,否则/失败时确定性截断。"""
        if str(self.config.get("context.summarizer", "deterministic")) != "llm":
            return truncate(failure, 2000)
        try:
            backend = self._role_backend("validator")
            prompt = FAILURE_COMPRESS_PROMPT.format(title=title, attempt=attempt,
                                                    failure=truncate(failure, 3000))
            resp = backend.complete([Message("user", prompt)], tools=None, temperature=0.1)
            return (resp.content or "").strip() or truncate(failure, 2000)
        except Exception:
            return truncate(failure, 2000)

    def _emit(self, event: dict) -> None:
        """语义事件出口;埋点不拖垮主链路,任何异常吞掉。"""
        if self.on_event is None:
            return
        with contextlib.suppress(Exception):
            self.on_event(event)

    # ------------------------------------------------------------------
    # 对外主循环
    def run(self, goal: str | None = None, task_id: str | None = None) -> dict:
        task_id = task_id or ("orch-" + short_id())
        self._task_id = task_id
        self._used_tokens = 0
        self.memory = WorkingMemory()
        self.archive = RetryArchive(compress_fn=self._compress_failure)
        if self._resumed_snapshot is not None:
            raw = self._resumed_snapshot
            self._resumed_snapshot = None
            self._goal, round_no, validated, self._tasks, self._checklist, records = \
                restore_state(raw)
            self.archive.restore(records)
            start_round = round_no + 1 if validated else max(round_no, 1)
            self._emit({"type": "orchestration_resume", "task_id": task_id,
                        "from_round": start_round, "tasks": len(self._tasks)})
        else:
            if not goal:
                raise ValueError("未提供目标(goal),也未加载续跑快照")
            self._goal = goal
            self._tasks, self._checklist = self.planner.plan(goal)
            self._sanitize_deps()
            start_round = 1
        self._emit({"type": "orchestration_start", "task_id": task_id,
                    "subtasks": [t.id for t in self._tasks], "goal": self._goal})
        self._write_snapshot(validated=False)

        success = False
        stop_reason = "达到最大轮数上限"
        round_no = start_round - 1
        for round_no in range(start_round, self.max_rounds + 1):
            self._round_no = round_no
            self._emit({"type": "orchestration_round_start", "task_id": task_id,
                        "round": round_no})
            self._execute_pending_tasks()

            if self.validator is not None:
                verdict = self.validator.verify(self._goal, self._checklist, self._tasks)
            else:
                verdict = self._auto_verdict()
            if verdict.completed and self._checklist.is_complete:
                success = True
                stop_reason = "Completion Checklist 验收通过"
                self._emit({"type": "orchestration_round_end", "task_id": task_id,
                            "round": round_no, "result": "accept"})
                self._write_snapshot(validated=True)
                break

            # 未通过 → 缺失项精确回流(BLOCKED/FAILED 任务注记并入)
            missing = list(verdict.missing_requirements)
            for t in self._tasks:
                if t.status is TaskStatus.BLOCKED:
                    missing.append(f"任务 {t.id}({t.title}) 被阻塞: "
                                   f"{t.result_summary},需规划绕行路径")
                elif t.status is TaskStatus.FAILED:
                    missing.append(f"任务 {t.id}({t.title}) 重试耗尽仍失败: "
                                   f"{t.result_summary},需拆成更小步骤")
            self._emit({"type": "orchestration_round_end", "task_id": task_id,
                        "round": round_no, "result": "reject", "missing": missing[:4]})
            self._write_snapshot(validated=False)
            if round_no == self.max_rounds:
                break
            new_tasks = self.planner.replan(self._goal, self._tasks, missing,
                                            activity=self.memory.recent_activity(8))
            if not new_tasks and not any(t.status is TaskStatus.PENDING for t in self._tasks):
                stop_reason = "无 PENDING 任务且重规划未产出新任务,无法继续推进"
                break
            self._tasks.extend(new_tasks)
            self._sanitize_deps()

        summary = self.aggregate(self._tasks)
        artifact = {
            "task_id": task_id, "goal": self._goal, "success": success,
            "rounds": round_no if round_no >= 1 else 0, "stop_reason": stop_reason,
            "checklist": self._checklist.to_dict(),
            "subtasks": [t.to_dict() for t in self._tasks], "summary": summary,
            "activity": self.memory.all_activity(),
        }
        self._export(artifact)
        self._emit({"type": "orchestration_end", "task_id": task_id, "summary": summary})
        return artifact

    # 对外:断点续跑
    def resume(self, task_id: str) -> dict:
        raw = load_snapshot(self._store, task_id)
        self._resumed_snapshot = raw
        return self.run(task_id=task_id)

    # ------------------------------------------------------------------
    # 单轮:工作队列(依赖就绪即可执行,失败任务轮内即时重入队)
    def _execute_pending_tasks(self) -> None:
        while True:
            if self._budget_exceeded():
                for task in [t for t in self._tasks if t.status is TaskStatus.PENDING]:
                    task.result_summary = (f"全局 token 预算耗尽(上限 {self.max_total_tokens}),"
                                           "任务未执行")
                    task.transition(TaskStatus.BLOCKED)
                    self.memory.add_task_event(task.id, "budget_blocked", task.result_summary or "")
                    self._emit({"type": "budget_exceeded", "task_id": self._task_id,
                                "task": task.id})
                return
            pending = [t for t in self._tasks if t.status is TaskStatus.PENDING]
            if not pending:
                return
            ready = [t for t in pending if self._deps_satisfied(t)]
            if not ready:
                for task in pending:
                    self._block_on_unmet_deps(task)
                return
            if self.max_workers > 1 and len(ready) > 1:
                with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                    list(pool.map(self._run_single, ready))
            else:
                self._run_single(ready[0])

    def _done_ids(self) -> set[str]:
        return {t.id for t in self._tasks if t.status is TaskStatus.DONE}

    def _budget_exceeded(self) -> bool:
        return self.max_total_tokens > 0 and self._used_tokens >= self.max_total_tokens

    def _sanitize_deps(self) -> int:
        """清理非法依赖:指向不存在任务或自身的 depends_on 直接剔除并留痕。"""
        known = {t.id for t in self._tasks}
        fixed = 0
        for task in self._tasks:
            valid = [d for d in task.depends_on if d in known and d != task.id]
            if valid != task.depends_on:
                fixed += len(task.depends_on) - len(valid)
                self._emit({"type": "deps_invalid", "task_id": self._task_id,
                            "task": task.id,
                            "dropped": [d for d in task.depends_on if d not in valid]})
                task.depends_on = valid
        return fixed

    def _deps_satisfied(self, task: Task) -> bool:
        done = self._done_ids()
        return all(dep in done for dep in task.depends_on)

    def _block_on_unmet_deps(self, task: Task) -> None:
        done = self._done_ids()
        unmet = [dep for dep in task.depends_on if dep not in done]
        task.result_summary = f"依赖未完成或不存在,任务无法启动: {unmet}"
        task.transition(TaskStatus.BLOCKED)
        self.memory.add_task_event(task.id, "task_blocked", task.result_summary or "")
        self._emit({"type": "subtask_blocked", "task_id": self._task_id, "sub": task.id,
                    "summary": task.result_summary})

    # ---- 单任务执行(每任务独立 harness/guard,线程池下互不污染)----
    def _run_single(self, task: Task) -> None:
        self._emit({"type": "subtask_start", "task_id": self._task_id,
                    "sub": task.id, "title": task.title})
        task.transition(TaskStatus.RUNNING)  # 状态机硬约束(attempts += 1)
        self.memory.add_task_event(task.id, "task_start", task.title)
        lessons = self.archive.render_for_task(task.id)  # Retry Archive 重试注入
        try:
            backend = self.backend_factory(task) if self.backend_factory else None
            harness = self._build_harness(task, backend)
            goal_text = task.title
            if task.description and task.description != task.title:
                goal_text += f"\n{task.description}"
            if task.done_criteria:
                goal_text += f"\n完成标准: {task.done_criteria}"
            goal_text += ("\n可用控制动作: submit_result(success, summary) 提交最终结论;"
                          "request_block(reason) 申报外部阻塞。")
            res = harness.run(TaskInput(task_id=f"{self._task_id}/{task.id}",
                                        goal=goal_text,
                                        extra={"retry_lessons": lessons}))
        except Exception as exc:  # 部分降级:单子任务失败不影响其余
            self._handle_failure(task, f"{type(exc).__name__}: {exc}")
            return
        self._used_tokens += (int(res.metrics.get("prompt_tokens_total", 0))
                              + int(res.metrics.get("completion_tokens_total", 0)))
        task.result_summary = res.final_answer or res.error or ""
        control = res.control or {}
        if control.get("action") == "request_block" or res.status == "blocked":
            task.transition(TaskStatus.BLOCKED)  # 执行者申报外部阻塞
            self.memory.add_task_event(task.id, "task_blocked", task.result_summary or "")
            self._emit({"type": "subtask_end", "task_id": self._task_id, "sub": task.id,
                        "status": TaskStatus.BLOCKED.value})
        elif control.get("action") == "submit_result" and not control.get("success"):
            self._handle_failure(task, task.result_summary or "执行者主动申报失败")
        elif res.status == "completed":
            task.transition(TaskStatus.DONE)
        else:
            self._handle_failure(task, task.result_summary or res.status)
        if control:
            # 子任务 harness 未接编排事件总线,控制收口由编排层代发
            self._emit({"type": "subtask_control", "task_id": self._task_id,
                        "sub": task.id, "action": control.get("action"),
                        "status": task.status.value})
        self.memory.add_task_event(task.id, "task_end",
                                   f"{task.status.value}: {task.result_summary}")
        self._emit({"type": "subtask_end", "task_id": self._task_id, "sub": task.id,
                    "status": task.status.value})
        self._write_snapshot(validated=False)

    def _handle_failure(self, task: Task, summary: str) -> None:
        """失败收口:FAILED →(有重试额度)归档并 PENDING 重入队,否则终态 FAILED。"""
        task.result_summary = summary
        task.transition(TaskStatus.FAILED)
        self._emit({"type": "subtask_end", "task_id": self._task_id, "sub": task.id,
                    "status": TaskStatus.FAILED.value})
        if task.attempts <= self.max_retries:
            record = self.archive.archive(task, summary)
            self.memory.add_task_event(task.id, "task_retry_scheduled", record.lessons)
            self._emit({"type": "task_retry_scheduled", "task_id": self._task_id,
                        "task": task.id, "attempt": task.attempts,
                        "lessons": record.lessons})
            task.transition(TaskStatus.PENDING)  # FAILED → PENDING(有重试额度)
        else:
            self.memory.add_task_event(task.id, "task_failed", summary)

    def _auto_verdict(self) -> ValidationVerdict:
        """确定性模式(无 Validator)的自动验收:全部 DONE 即通过并回填清单。"""
        tasks = self._tasks
        completed = bool(tasks) and all(t.status is TaskStatus.DONE for t in tasks)
        missing = [f"任务 {t.id} 未完成: {t.result_summary}"
                   for t in tasks if t.status is not TaskStatus.DONE]
        if completed:
            self._checklist.apply_verdict([
                {"item_id": i.item_id, "satisfied": True,
                 "evidence": "确定性模式(无 Validator)自动验收"}
                for i in self._checklist.items])
        return ValidationVerdict(completed=completed, missing_requirements=missing,
                                 summary="确定性模式:无 Validator")

    # ------------------------------------------------------------------
    @staticmethod
    def aggregate(tasks: list[Task]) -> dict:
        done = [t for t in tasks if t.status is TaskStatus.DONE]
        failed = [t for t in tasks if t.status is TaskStatus.FAILED]
        blocked = [t for t in tasks if t.status is TaskStatus.BLOCKED]
        return {"total": len(tasks), "completed": len(done), "failed": len(failed),
                "blocked": len(blocked),
                "failed_ids": [t.id for t in failed],
                "final_answers": {t.id: t.result_summary for t in done}}

    def _build_harness(self, task: Task, backend):
        from ..safety import AllowAllProvider
        from .harness import AgentHarness
        cfg = Config(self.config.to_dict())
        # 同一编排内的子任务共享一个交付工作区(批次④修正):目标级产物落在同一
        # 目录,后续任务可直接使用先任务的产出(dep-chain 类 compound 目标依赖此
        # 语义);跨编排仍完全隔离。记忆/工件按子任务隔离,断点键含子任务 id 天然隔离。
        base = Path(self.config.get("workspace.root", ".")) / f".orch_{self._task_id}"
        cfg.set("workspace.root", str(base / "ws"))
        cfg.set("memory.root", str(base / f"memory_{task.id}"))
        cfg.set("checkpoint.root", str(base / "checkpoints"))
        cfg.set("artifacts.root", str(base / f"artifacts_{task.id}"))
        cfg.set("observability.enabled", False)
        harness = AgentHarness.build(cfg, backend=backend, approver=AllowAllProvider())
        # 控制动作(批次②):注册 submit_result/request_block,子任务可用其收口
        harness.registry.register(SubmitResultTool())
        harness.registry.register(RequestBlockTool())
        allow = (task.extra or {}).get("allow_tools")
        if allow:
            harness.allowed_tools = set(allow) | CONTROL_TOOLS
        # 子任务内部事件(tool_call/step_end 等)以 sub 标签并入编排事件流
        def _sub_event(event: dict, _sub: str = task.id) -> None:
            self._emit({"sub": _sub, **event})
        harness.on_event = _sub_event
        return harness

    def _write_snapshot(self, validated: bool) -> None:
        if not self._store.enabled:
            return
        save_snapshot(self._store, self._task_id,
                      snapshot_to_dict(goal=self._goal, round_no=self._round_no,
                                       validated=validated, tasks=self._tasks,
                                       checklist=self._checklist,
                                       records=self.archive.all_records()))

    def _export(self, artifact: dict) -> None:
        root = Path(self.config.get("artifacts.root", ".agentmuster/artifacts")) / artifact["task_id"]
        root.mkdir(parents=True, exist_ok=True)
        (root / "orchestration.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
