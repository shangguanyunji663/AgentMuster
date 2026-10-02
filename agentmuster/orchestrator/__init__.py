"""多智能体编排层(移植自 miniMaster 角色层,快照 24f4247)。

模块职责:
  * tasks           —— 任务状态机(PENDING/RUNNING/DONE/FAILED/BLOCKED 硬约束迁移表)
  * checklist       —— Completion Checklist(目标验收清单)
  * structured      —— 后端无关的结构化 JSON 输出助手(解析失败反馈重试环)
  * planner/validator —— Planner / Validator 角色
  * working_memory  —— 编排层角色视图记忆(Planner/Validator 视图 + 有界活动日志)
  * retry_archive   —— 失败任务轨迹压缩归档,重试注入
  * snapshot        —— 编排层断点续跑快照(复用 CheckpointStore)

多轮闭环主循环在 agent/orchestrator.py 的 Orchestrator;本包只承载角色与机制。
"""
from .checklist import ChecklistItem, CompletionChecklist
from .retry_archive import RetryArchive, RetryRecord
from .structured import StructuredOutputError, structured_complete
from .tasks import ALLOWED_TRANSITIONS, IllegalTransitionError, Task, TaskStatus

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ChecklistItem",
    "CompletionChecklist",
    "IllegalTransitionError",
    "RetryArchive",
    "RetryRecord",
    "StructuredOutputError",
    "Task",
    "TaskStatus",
    "structured_complete",
]
