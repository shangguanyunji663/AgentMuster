"""编排层断点续跑快照:Orchestrator 状态 ↔ checkpoint 存储的序列化与恢复。

复用 CheckpointStore(同一 checkpoint.root,键加 -orchestration 后缀),保存:
目标、轮次进度、任务全量(状态/尝试/结论/依赖)、Checklist、Retry Archive。
子任务的原始执行轨迹不入快照(由子任务自身 checkpoint 承载)——快照轻量、
恢复语义清晰:validated=True 从下一轮继续,False 重做当前轮(DONE 任务不重跑)。
"""
from __future__ import annotations

from dataclasses import asdict

from ..checkpoint import CheckpointStore
from .checklist import CompletionChecklist
from .retry_archive import RetryRecord
from .tasks import Task

SNAPSHOT_VERSION = 1


def snapshot_key(task_id: str) -> str:
    return f"{task_id.replace('/', '_')}-orchestration"


def snapshot_to_dict(goal: str, round_no: int, validated: bool, tasks: list[Task],
                     checklist: CompletionChecklist, records: list[RetryRecord]) -> dict:
    return {
        "version": SNAPSHOT_VERSION,
        "goal": goal,
        "round_no": round_no,
        "validated": validated,
        "tasks": [t.to_dict() for t in tasks],
        "checklist": checklist.to_dict(),
        "archive": [asdict(r) for r in records],
    }


def save_snapshot(store: CheckpointStore, task_id: str, state: dict) -> None:
    store.save(snapshot_key(task_id), state)


def load_snapshot(store: CheckpointStore, task_id: str) -> dict:
    raw = store.load(snapshot_key(task_id))
    if raw is None:
        raise ValueError(f"找不到编排断点: {task_id}")
    if int(raw.get("version", 0)) != SNAPSHOT_VERSION:
        raise ValueError(f"不支持的快照版本: {raw.get('version')}(期望 {SNAPSHOT_VERSION})")
    return raw


def restore_state(raw: dict) -> tuple[str, int, bool, list[Task], CompletionChecklist, list[RetryRecord]]:
    """从快照 dict 重建 (goal, round_no, validated, tasks, checklist, archive 记录)。"""
    goal = str(raw["goal"])
    round_no = int(raw.get("round_no", 0))
    validated = bool(raw.get("validated", False))
    tasks = [Task.from_dict(d) for d in raw.get("tasks", [])]
    checklist = CompletionChecklist.from_dict(raw.get("checklist", {}))
    records = [RetryRecord(**r) for r in raw.get("archive", [])]
    return goal, round_no, validated, tasks, checklist, records
