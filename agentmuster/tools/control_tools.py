"""控制工具:submit_result / request_block(移植自 miniMaster Executor 控制动作)。

不进默认注册表(build_registry 不含);由编排层为子任务 harness 追加注册,
使其出现在工具 schema 中供模型调用。AgentHarness 在工具分发阶段识别这两个
动作并终止主循环(不走安全链、不执行业务):
  * submit_result(success, summary) → status=completed,final_answer=summary,
    RunResult.control={"action","success"};success=False 由编排层判 FAILED(可重试);
  * request_block(reason)           → status=blocked(批次② 新增状态),
    final_answer=reason,由编排层转 BLOCKED。
"""
from __future__ import annotations

from .base import SAFE, Tool, ToolContext, ToolResult

SUBMIT_RESULT = "submit_result"
REQUEST_BLOCK = "request_block"
CONTROL_TOOLS: frozenset[str] = frozenset({SUBMIT_RESULT, REQUEST_BLOCK})


class SubmitResultTool(Tool):
    name = SUBMIT_RESULT
    description = "提交当前子任务的最终结论并结束任务。summary 需含可验证证据。"
    danger = SAFE
    parameters = {  # noqa: RUF012 - 类级 schema 常量(非实例可变状态)
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "任务是否成功完成"},
            "summary": {"type": "string", "description": "执行结论与证据"},
        },
        "required": ["success", "summary"],
    }

    def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        # 控制动作不经此处执行:AgentHarness 在分发前拦截并终止主循环
        return ToolResult(output="[控制动作] submit_result 已由 Harness 受理", ok=True,
                          meta={"control": SUBMIT_RESULT})


class RequestBlockTool(Tool):
    name = REQUEST_BLOCK
    description = "任务因外部因素无法推进(缺依赖/权限等)时申报阻塞并说明原因。"
    danger = SAFE
    parameters = {  # noqa: RUF012 - 类级 schema 常量(非实例可变状态)
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "阻塞原因"},
        },
        "required": ["reason"],
    }

    def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        return ToolResult(output="[控制动作] request_block 已由 Harness 受理", ok=True,
                          meta={"control": REQUEST_BLOCK})
