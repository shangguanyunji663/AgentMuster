# MERGE_DESIGN：miniMaster 角色层移植设计（接口对齐 + 分批计划 + 测试计划）

> 状态：✅ 已评审共识（grilling 决策树三轮访谈，2026-10-02）｜**批次①-⑤ 已全部合入**（见 CHANGELOG [Unreleased]）；Layer 7 真实模型跑批待手动执行
> 基线：mycoder `main` @ `7eae67c`（AgentMuster 继承其全部 git 历史）｜miniMaster 快照 @ `24f4247`（80 文件，本地 git 仓库）
> 本文档是合并工作的执行依据；每批合入时更新本文状态标记与 CHANGELOG。
>
> **执行期修订**（相对原设计）：
> 1. §5.6 WorkingMemory 落地比设计更精简——D1 定案后 Executor 视图消失，三级裁剪机随之移除（留之即死代码），只保留角色视图渲染 + 有界活动日志；教训压缩由 RetryArchive 承担。
> 2. §5.3 批次④ 修正：同一编排内的子任务**共享交付工作区**（`.orch_<orch_id>/ws`）——原"每子任务完全隔离"会拆散 dep-chain 类 compound 目标；跨编排仍完全隔离，memory/artifacts 仍按子任务隔离。
> 3. 协议降级/截断自愈以纯 urllib 实现，未引入 openai SDK（较原计划 `[llm]` extra 更强，核心零依赖不变）。

---

## 1. 决策记录

| # | 决策点 | 结论 |
|---|--------|------|
| D1 | 子任务执行架构 | **单循环改造**：子任务仍由 `AgentHarness.run()` 执行；miniMaster 角色机制注入底座，不引入第二套主循环 |
| D2 | Orchestrator 语义 | **多轮闭环**（执行 → Checklist 验收 → replan）；对外 `run(goal) -> artifact` 签名兼容，返回增加 `rounds` / `checklist` 字段 |
| D3 | 仓库形态 | 新仓库 **AgentMuster**，继承 mycoder 全部 git 历史（本地 clone 改名，远端待建） |
| D4 | 原仓库处置 | mycoder 原样不动；miniMaster 仅做本地 git 快照（`24f4247`），不做归档公告 |
| D5 | 包名 | 批次① 内 `mycoder` → **`agentmuster`**（机械重命名独立成提交，压在批次① 最前） |
| D6 | 版本与依赖 | Python **≥3.11**；`openai` 进 optional extra `[llm]`，核心保持"仅 PyYAML"零依赖叙事 |
| D7 | CI | **完整恢复**：双 OS 矩阵 + ruff + mypy + pytest + 覆盖率门禁（orchestrator ≥90%，全局 ≥75%） |
| D8 | 角色视图记忆 | WorkingMemory **拆解移植**（只留 Planner/Validator 视图）→ `orchestrator/working_memory.py`；StructuredMemory 不动 |
| D9 | LiveContextTrimmer | **不移植组件**；其 tool_calls 配对边界用例改写为 ContextManager 回归测试 |
| D10 | 编排层断点续跑 | **进批次①**：orchestration 快照复用 CheckpointStore，`Orchestrator.resume(task_id)` 一并交付 |
| D11 | 节奏 | 分 5 批合入，每批全量测试绿 + CHANGELOG 条目 |

**默认采纳项**（随上述决策推导，不再逐条评审）：

- MCP stdio 客户端 → `tools/mcp_client.py`，远端 schema 映射进 `ToolRegistry`；
- 协议双模式降级（NATIVE→TEXT_JSON）+ `finish_reason=length` 截断自愈 → 并入 `LocalOpenAIBackend`，并补齐 miniMaster 的测试盲区（该文件原覆盖率约 32%）；
- miniMaster 8 任务真实基准 + 客观检查器 + `--ablate` 消融开关 → eval Layer 7（手动跑，不进 CI）；
- 两套 JSON 提取 / 截断工具函数合并为 `util.py` 一份实现；
- 死代码清理随批：`memory/retriever.py`（零调用）、根目录 `generate_test_file.py`（4669 行生成产物）已删除；`keep_last_tool_results` / `compressible_age` 两个声明未生效的配置项已清除，`context.budget_tokens` 经核查仍在评测运行器 `EvalRunner._cfg_for()` 与 stdlib `/health` 中生效，予以保留（未随批删除）；
- `Task`（状态机版）替代 `SubTask`；每轮内对依赖就绪的任务并行；角色提示词 → `agent/prompts.py`；配置键走 `orchestrator.*` 点式命名。

## 2. 目标与非目标

**目标**：把 miniMaster 的多智能体角色闭环（Planner-Executor-Validator + 四重纠错）嫁接到 mycoder 的单 Agent 运行底座上，形成"单 Agent 底座 / 多智能体编排 / 七层评测"三层结构；全程保持 272+ 项离线测试全绿、核心零依赖、MockBackend 可复现。

**非目标**：

- 不引入 LangChain / LangGraph 等编排框架（手写编排是两个项目共同的路线）；
- 不追求 miniMaster 逐行保真——语义保真优先，接口向 mycoder 惯例对齐；
- 不动 `kb_lora` 微调线与 `benchmarks/` 目录（维持现状，另行规划）；
- 不在本合并中做旧仓库的归档/删除（D4）。

## 3. 现状接口盘点（移植的事实基础）

### 3.1 AgentMuster 基座（mycoder @ `7eae67c`）

- `agent/orchestrator.py`：`Orchestrator(config, planner: Callable[[str], list[dict]] | None, backend_factory, max_workers, on_event)`；`_default_planner` 确定性空壳（orchestrator.py:36-38，永远返回单子任务）；`run()` 一次性分解 → ThreadPoolExecutor 并行 → `aggregate()` → `orchestration.json` 工件；`_build_harness()` 为每个子任务建完全隔离的 AgentHarness（workspace/memory/checkpoint/artifacts 四根独立，orchestrator.py:110-122，审批用 AllowAllProvider）。
- `agent/harness.py`：`AgentHarness.build/run(TaskInput)/resume(task_id)`；主循环 = 组装上下文 → `backend.complete(messages, registry.schemas())` → 工具执行（安全链）→ 记忆沉淀 → checkpoint；空终答温和重问一次（`_EMPTY_ANSWER_REMINDER`）；`RunResult.status ∈ {completed, max_steps, error, interrupted}`。
- `models/base.py`：`ModelBackend.complete(messages, tools, temperature=0.0) -> ModelResponse(content, tool_calls: list[dict], finish_reason, usage)`；`state()/load_state()` 供 checkpoint 游标。
- `models/mock.py`：MockBackend 脚本回放——`script` 为逐轮 `{"tool_calls":[...]}` 或 `{"content": "..."}`，`from_recipe()` 快捷构造，游标可恢复。**结构化 JSON 场景可直接用 `{"content": "<json 文本>"}` 脚本项驱动**。
- `safety/guard.py`：`SafetyGuard` 检查链 schema 校验 → 路径隔离 → shell 黑白名单 → 去重缓存 → HITL 审批；`GuardResult(allowed, needs_approval, reason, cached_output, danger, action)`（guard.py:99-106）。
- `api/event_bus.py`：`TaskEventBus.on_event` 按 `event["task_id"]` 路由进 SSE 队列，**无事件类型白名单**——新增事件类型天然可达 SSE。
- 打包：`pyproject.toml` name=`mycoder-harness`，`requires-python>=3.10`，console script `mycoder=mycoder.cli:main`，extras `http/test/dev/api/vector/otel`，coverage `source=["mycoder"]`；仓库根有 Dockerfile / docker-compose.yml / environment.yml / CHANGELOG.md。

### 3.2 miniMaster 快照（@ `24f4247`）

- `core/harness.py`：三层嵌套轮次循环（harness.py:177-261）——`planner.plan()` → `_execute_pending_tasks()`（全局 token 预算熔断 → 依赖就绪任务可并行 → 失败任务轮内即时重入队）→ `validator.verify()` → missing 精确回流 → `planner.replan()`；每任务收口与每轮结束写快照。
- `core/state_machine.py`：`TaskStatus ∈ {PENDING, RUNNING, DONE, FAILED, BLOCKED}` + `ALLOWED_TRANSITIONS` 迁移表硬约束（非法迁移抛 `IllegalTransitionError`）；`Task` 携带 `title/description/done_criteria/depends_on/attempts/result_summary`。
- `core/action_policy.py`：`Role` 三角色 + `ActionPolicy` 动作白名单（Executor 的工具白名单由 ToolService 注册表动态并入），越权抛 `PolicyViolation`。
- `core/guard.py`：`RepeatedActionGuard` 三重死循环检测——连续重复（max_repeat）/ 窗口计数（window_size 内 ≥ window_max）/ 周期振荡（A→B→A→B，步长 2~3），命中即拦截并回灌引导语。
- `core/checklist.py`：`CompletionChecklist` + `apply_verdict()/unmet()/is_complete`，纯数据类。
- `agents/planner.py`：`plan()` 产出 `(tasks, checklist)`，空任务语义重问一次，checklist 缺失时从任务 done_criteria 兜底派生；`replan()` 增量补任务。
- `agents/executor.py`：瘦循环（模型调用 → 白名单 → Guard → 分发），控制动作 `submit_result` / `request_block`（executor.py:37-57），TEXT_JSON 协议单动作假设。
- `agents/validator.py`：`verify()` → `ValidationVerdict(completed, missing_requirements, summary)`，判定写回 Checklist。
- `memory/working_memory.py`：三级裁剪（单结果截断 → 超阈值 LLM 压缩 → 最近 N 步保留）+ 三角色视图渲染（executor/planner/validator），读写均持锁。
- `memory/retry_archive.py`：失败轨迹 LLM 压缩归档为「原因+教训」，重试时注入 Executor 上下文。
- `core/snapshot.py`：轮级快照 `{version, goal, round_no, validated, tasks, checklist, archive, workdir}` + `restore_state()`。
- `llm/client.py`：NATIVE→TEXT_JSON 协议自动降级（通道异常与"未按协议输出"双触发）、`finish_reason=length` 2×max_tokens 截断自愈（上限 32768）、`chat_structured()` 解析失败反馈重试环、流式故障永久回落非流式、`last_prompt_tokens` 真实用量记录。
- `tools/service.py`：`ToolService.register/names/schemas/render_catalog/dispatch`，统一参数校验与输出截断。
- `tests/`：84 项（`fakes.py` FakeLLM 替身 + `mcp_fake_server.py` 真实子进程 MCP 桩）。

## 4. 接口对齐矩阵

| # | miniMaster 源 | 去处（agentmuster/…） | 适配要点 | 批次 |
|---|---------------|----------------------|----------|------|
| 1 | `core/state_machine.py`（Task/TaskStatus/迁移表） | `orchestrator/tasks.py` | 替代 `SubTask`；`to_dict()/from_dict()` 进 orchestration 工件与快照 | ① |
| 2 | `core/checklist.py` | `orchestrator/checklist.py` | 原样移植（纯数据类零依赖） | ① |
| 3 | `agents/planner.py` | `orchestrator/planner.py` | `chat_structured` → `orchestrator/structured.py`（后端无关版）；`reporter.emit` → `on_event` | ① |
| 4 | `agents/validator.py` | `orchestrator/validator.py` | 同上；保留 WorkingMemory 的 validator 视图 | ① |
| 5 | `agents/executor.py` 瘦循环 | **不整体移植**（D1） | 存活件：控制动作 → `tools/control_tools.py`（②）；retry lessons 注入 → `TaskInput.extra`（①）；no-tool 纠偏与基座空答重问合并 | ①/② |
| 6 | `core/action_policy.py` + `agents/base.py` | `safety/policy.py` | `SafetyGuard.check()` 增 `allowed_tools` 参数；PolicyViolation 语义并入 GuardResult 拒绝路径 | ② |
| 7 | `core/guard.py` RepeatedActionGuard | `safety/repeat_guard.py` | SafetyGuard 可选成员（每子任务独立实例）；检查顺序：schema→路径→shell→去重→repeat→HITL | ② |
| 8 | `core/harness.py` 轮次循环 | `agent/orchestrator.py` 重写 | 并行语义从"跨子任务"改为"轮内就绪任务"；保留 legacy `Callable[[str],list[dict]]` planner 适配器 | ① |
| 9 | `core/snapshot.py` | `orchestrator/snapshot.py` | 复用 `CheckpointStore` 落盘（key=`orch-<id>`），不另造存储 | ① |
| 10 | `memory/working_memory.py` | `orchestrator/working_memory.py` | 删 Executor 视图（D8）；`compress_fn` 接 `context.summarizer` | ① |
| 11 | `memory/retry_archive.py` | `orchestrator/retry_archive.py` | `compress_fn` = Summarizer 适配（LLM 失败回退确定性） | ① |
| 12 | `memory/live_context.py` | 不移植（D9） | tool_calls 配对用例 → `tests/test_context.py` | ③ |
| 13 | `llm/client.py` 协议降级/截断自愈/流式回落 | `models/local_openai.py` | 随 extra `[llm]` 懒加载；`_parse_text_action`/`extract_json` 合并进 `util.py` | ③ |
| 14 | `llm/client.py` `chat_structured` | `orchestrator/structured.py` | 改为 `structured_complete(backend, messages)` 后端无关版 | ① |
| 15 | `utils/json_tools.py` | `util.py` | 与现有 `truncate` 等合并，测试随迁 | ① |
| 16 | `tools/mcp_client.py` + MCPProxyTool | `tools/mcp_client.py` | 适配 `Tool` 基类（name 前缀 `mcp_`，danger=WARN 走审批策略）；`build_registry` 增 mcp 入参 | ③ |
| 17 | `prompts/builder.py` + `templates.py` | `agent/prompts.py` | 三角色 system message 模板化，变量显式注入 | ① |
| 18 | `eval/run_eval.py` + 8 任务 | `eval/layer7_multiagent.py` + `eval/tasks/` | 客观检查器 + `--ablate` → `orchestrator.ablate` 配置 | ④ |
| 19 | `config.py` Settings（纯 env） | `config.py` DEFAULT YAML 键 | 环境变量降级为容器/CI 覆盖层 | ①/②/③ |
| 20 | `utils/reporter.py` | 不移植 | 事件直连 `on_event` | ① |
| 21 | `tests/*`（84 项） | 见 §7.2 映射表 | 逐文件给出去处与取舍 | ①-③ |

## 5. 关键设计

### 5.1 AgentHarness 侧的五处增强点（D1 的落地）

1. **retry lessons / done_criteria 注入（①）**：`AgentHarness._run` 读取 `task.extra["retry_lessons"]` 与 `task.extra["done_criteria"]`，追加进 `context.set_task()` 的记忆块——子任务执行时能看到历史失败教训与验收标准，Harness 改动 <10 行。
2. **控制工具（②）**：`submit_result(success, summary)` / `request_block(reason)` 注册为内置 `Tool`（不进默认 registry，由编排子任务装配时追加）；`_execute_tools` 前置拦截识别，命中后终止主循环：`final_answer=summary`，status 记 `completed` 或新增 `blocked`。
3. **ActionPolicy 并入安全链（②）**：`SafetyGuard.check(tool, params, allowed_tools=None)`——`allowed_tools` 非空且不含当前工具名时拒绝，拒绝理由沿用 miniMaster 的越权文案（含白名单列表，回灌逼模型纠偏）；缺省 None = 不限（保持现有 272 项测试行为不变）。
4. **RepeatedActionGuard 并入安全链（②）**：SafetyGuard 增可选 `repeat_guard` 成员；编排层每子任务 new 一个实例（指纹状态天然隔离）；`cache_hit`（去重短路）是否计入窗口做成配置 `safety.repeat_guard.count_cache_hits`（默认计）。
5. **RunResult.status 扩展（②）**：新增 `"blocked"`。下游同步清单：`api/fastapi_server` 状态透传、监控页状态徽标、eval 断言、`aggregate()` 的失败口径。

### 5.2 结构化输出助手（①）

新增 `orchestrator/structured.py`：

```
structured_complete(backend, messages, max_attempts=3) -> dict
  resp = backend.complete(messages)          # 不传 tools，纯文本
  try extract_json(resp.content)             # util 合并版
  except/truncated → 追加 assistant+user 反馈消息，重试
  耗尽 → raise StructuredOutputError
```

后端无关：MockBackend 用 `{"content": "<json>"}` 脚本驱动，LocalOpenAIBackend 走真实模型；miniMaster 的 `force_json` / `response_format` 增强放批次③随协议降级一并考虑（`orchestrator.roles.*.force_json_mode` 可选配置）。

**角色模型路由**：`orchestrator.roles.planner.model` / `validator.model` 非空时，`Orchestrator` 用 `Config` 克隆 + 覆盖 `model.local_openai.model` 后 `create_backend()` 出角色专用后端（懒构造、进程内缓存）；空 = 主后端。温度走 `structured_complete(temperature=...)`。

### 5.3 多轮 Orchestrator（①）

```
run(goal, task_id=None):
    emit(orchestration_start)
    if resume: restore(tasks/checklist/archive/round_no) else:
        tasks, checklist = planner.plan(goal)     # 无 backend → 确定性单任务+goal 兜底 checklist
        sanitize_deps(); snapshot(validated=False)
    for round in start_round..max_rounds:
        execute_ready_tasks()                     # PENDING 且依赖就绪 → ThreadPool 并行；
                                                  # 预算熔断 → 全部 PENDING 转 BLOCKED
        verdict = validator.verify(goal, checklist, tasks)
        if verdict.completed and checklist.is_complete: success; snapshot(True); break
        missing = verdict.missing_requirements + BLOCKED/FAILED 任务注记
        emit(round_end, reject)
        if round == max_rounds: break
        new = planner.replan(goal, tasks, missing)
        if not new and 无 PENDING: stop_reason=...; break
        tasks += new; sanitize_deps(); snapshot(True)
    artifact = {task_id, goal, rounds, stop_reason, checklist, subtasks: [t.to_dict()], summary}
    emit(orchestration_end)
```

**兼容性**：`planner` 入参保留——传 `Callable[[str], list[dict]]` 时包一层 `_LegacyPlannerAdapter`（产出单角色确定性闭环：无 Validator LLM 判定，checklist 从子任务 done_criteria 派生并默认全部满足），旧测试与外部注入方不破坏；新代码统一用 `PlannerRole`。

**事件映射**（全部带 `task_id=<orch id>`，EventBus 无白名单直接可达 SSE）：

| miniMaster 事件 | AgentMuster 事件 | 批次 |
|---|---|---|
| harness_start | orchestration_start（已有） | ① |
| plan_created | orchestration_plan（新） | ① |
| task_start / task_done / task_blocked / task_failed | subtask_start（新）/ subtask_end（已有，status 扩展） | ① |
| round_end | orchestration_round_end（新） | ① |
| validated | orchestration_validated（新） | ① |
| replan | orchestration_replan（新） | ① |
| task_retry_scheduled / deps_invalid / budget_exceeded | 同名（新） | ① |
| guard_block / policy_violation | 同名（新） | ② |
| harness_end | orchestration_end（已有，summary 扩展） | ① |

### 5.4 预算熔断（①）

`orchestrator.max_total_tokens`（默认 800000，0=不限）：每轮收口后累加各子任务 `RunResult.metrics` 的 prompt+completion tokens，超限 → 全部 PENDING 转 `BLOCKED`（result_summary 注明预算耗尽）+ `budget_exceeded` 事件；Validator 对 BLOCKED 任务产生"需绕行"缺失项，由 replan 响应。

### 5.5 编排快照与续跑（①）

- 快照 payload：`{version, goal, round_no, validated, tasks[], checklist, archive[], subtask_roots}`，经 `CheckpointStore.save("orch-<id>", ...)` 落盘——复用现有存储与脱敏纪律，不新建机制。
- `Orchestrator.resume(task_id)`：`validated=True` → 从 `round_no+1` 轮继续；`False` → 本轮重跑（已 DONE 任务不重复执行）。
- 子任务级：快照时 RUNNING 的子任务按重试语义整任务重跑（首版语义，见开放点 O1）；子任务自身的 AgentHarness checkpoint 独立生效，不受编排层影响。

### 5.6 记忆分工（D8）

| 层 | 模块 | 职责 |
|---|---|---|
| 编排层 | `orchestrator/working_memory.py` | 跨任务工作记忆：Planner replan 时看任务状态与结论、Validator 验收时看 Checklist+结论；三级裁剪（截断/LLM 压缩/滚动窗口）；线程安全已内置 |
| 编排层 | `orchestrator/retry_archive.py` | 失败任务轨迹压缩归档与重试注入 |
| 子任务层 | `memory/store.py`（现有） | 单任务内文件记忆、混合检索、follow-up 摘要注入——**零改动** |

压缩函数适配：`CompressFn` 统一接 `context.summarizer`（`context.summarizer=llm` 时用 LLMSummarizer，自带确定性回退；否则确定性摘要）。

### 5.7 并行与线程安全（①）

- 就绪任务并行沿用 ThreadPoolExecutor（`orchestrator.parallel`）；每子任务独立 `.orch_<id>` 根（现有机制）+ 独立 Guard/Policy 实例。
- 已知并发点：各子任务 `StructuredMemory.save()` 在收尾并发写盘 → 编排层加互斥锁串行化（风险 R3）。
- WorkingMemory 原生带读写锁与压缩锁，直接可用。

### 5.8 配置新增键（DEFAULT 追加）

```yaml
orchestrator:            # 批次①
  max_rounds: 3
  max_retries: 2
  parallel: 1
  max_total_tokens: 800000
  roles:
    planner:   {model: "", temperature: 0.2}
    validator: {model: "", temperature: 0.0}
  ablate: []             # 批次④: guard|retry|budget|policy|validator
safety:                  # 批次②
  action_policy_enabled: true
  repeat_guard: {enabled: true, max_repeat: 2, window_size: 12, window_max: 4, count_cache_hits: true}
tools:                   # 批次③
  mcp: {server_cmd: "", timeout: 30.0}
model.local_openai:      # 批次③
  protocol_fallback: true
  truncation_self_heal: true
  max_tokens_ceiling: 32768
```

### 5.9 协议降级与截断自愈（③）

`local_openai.py` 移植点：`protocol_mode` 状态机（通道异常与"未按协议输出"双触发降级，永久单向）；TEXT_JSON 模式把工具目录注入 system message（`render_catalog` 逻辑内联）；`finish_reason=length` 且无 tool_calls → 2×max_tokens 重试一次（ceiling 32768）；流式故障永久回落非流式（现有 stream 代码保留，补降级）。依赖 `openai>=1.40,<3` 进 extra `[llm]`，模块内懒 import 保核心零依赖。

### 5.10 MCP 接入（③）

`tools/mcp_client.py`（零依赖 stdio JSON-RPC，含进程树清理）原样移植；`MCPProxyTool` 适配为 `Tool` 子类：`name = f"mcp_{tool_name}"`，`danger=WARN`（写类操作走 HITL 策略），`execute(ctx, **params)` → `client.call()`；CLI/装配层按 `tools.mcp.server_cmd` 连接，失败降级纯内置工具 + `mcp_unavailable` 事件。

### 5.11 评测 Layer 7（④）

- `eval/layer7_multiagent.py`：8 个任务（hello / fizzbuzz / calc / dep-chain / parallel-files / codebase-grep / r2-bugfix / r2-codebase-grep）定义迁入 `eval/tasks/*.json`（工作区 fixture 由 runner 现场生成，不再携带运行产物）。
- 客观检查器沿用 miniMaster 口径（文件存在性 + 内容断言 + 执行结果比对）。
- `--ablate guard|retry|budget|policy|validator` 逐项关闭机制跑对照，量化各机制贡献——这是"编排层价值"的硬数字来源。
- 与 Layer 6/6b 三臂对照的关系：Layer 7 独立成层（多智能体端到端，真实模型手动跑），报告含 ablate 对照表。

## 6. 分批计划

### 批次①：包名 + 角色层（D5/D10）

- **c1（机械重命名，零逻辑变更）**：`mycoder/` → `agentmuster/`；pyproject（name=`agentmuster`、console script `agentmuster=agentmuster.cli:main`、packages/package-data/coverage source）；logger 名；Dockerfile / docker-compose.yml / environment.yml / 文档引用全量替换；`requires-python>=3.11`；console script 保留 `mycoder` 别名一个版本周期。验收：全量 272 测试绿 + ruff/mypy 绿。
- **c2（角色层）**：`orchestrator/` 包八件套（tasks/checklist/structured/planner/validator/working_memory/retry_archive/snapshot）+ orchestrator 多轮重写 + AgentHarness 增强点 1 + `agent/prompts.py` + 配置键 + 事件 + resume。
- 测试：§7.1 场景 S1-S12 + §7.2 映射表批次① 部分；CHANGELOG 条目。

### 批次②：安全增强

- `tools/control_tools.py`（submit_result/request_block）+ RunResult.status=`blocked` 下游同步；`safety/policy.py` + `safety/repeat_guard.py` 并入 SafetyGuard 检查链；`agentmuster.ablate` 预留口。
- 测试：控制动作终止语义、越权回灌、Guard 三重规则、cache_hit 计窗开关、全链回归。

### 批次③：LLM 协议 + MCP + 上下文回归

- §5.9 协议降级/截断自愈 + extra `[llm]`；§5.10 MCP；LiveContextTrimmer 配对用例并入 test_context（D9）；死配置项处置。
- 测试：协议状态机（FakeOpenAI 客户端）、MCP 子进程往返、上下文回归。

### 批次④：评测 Layer 7

- §5.11 全部内容；`--ablate` CLI 口；报告工件。
- 验收：真实模型（本地 OpenAI 兼容端点）8/8 + ablate 对照报告（手动，不入 CI）。

### 批次⑤：CI + 文档收尾

- `.github/workflows/ci.yml`：矩阵 `ubuntu-latest / windows-latest` × `3.11 / 3.12`；ruff + mypy + pytest-cov；覆盖率门禁（§7.3）；借 miniMaster 现成 `ci.yml` 骨架（快照 `.github/` 内已有）。
- README 重构（三层故事 + 演进说明）、ARCHITECTURE 更新、CHANGELOG 收尾、本文档状态更新。

**每批 DoD**：pytest 全量绿 + ruff/mypy 绿 + CHANGELOG 条目 + SSE 监控页不回归。

## 7. 测试计划

### 7.1 MockBackend 脚本回放场景（批次①，tests/orchestrator/）

| # | 场景 | 脚本要点 | 关键断言 |
|---|------|----------|----------|
| S1 | 单轮闭环 | planner JSON（1 任务+checklist）→ 子任务 from_recipe 读写文件 → 终答 → validator JSON 全 satisfied | success=True，rounds=1，artifact.checklist 全 [x] |
| S2 | 验收驳回→replan | validator 第一轮 missing → replan 增任务 → 第二轮通过 | rounds=2，orchestration_replan 事件，新增任务 id 递增 |
| S3 | checklist 缺失兜底 | planner 输出无 checklist | 从任务 done_criteria 派生 items，验收可达 |
| S4 | planner 空任务重问 | 首轮 JSON `tasks: []` → 反馈后重试 | structured_complete 重试环，第二条消息含反馈文案 |
| S5 | 依赖调度 | B depends_on [A] | A 先于 B；环形/自依赖被 sanitize 剔除 + deps_invalid 事件 |
| S6 | 失败重试+教训注入 | 子任务 submit success=false → FAILED → 重入队 | 第二次执行 system prompt 含 retry_lessons；archive 记录 1 条 |
| S7 | 重试耗尽→绕行 | 子任务连续 FAILED 至 max_retries | 任务终态 FAILED，replan 收到"拆成更小步骤"缺失项 |
| S8 | 预算熔断 | max_total_tokens 调小 | PENDING→BLOCKED + budget_exceeded 事件 + validator 缺失回流 |
| S9 | 状态机硬约束 | 直接构造非法迁移 | IllegalTransitionError 抛出与消息 |
| S10 | 并行隔离 | 2 个无依赖任务 + parallel=2 | 各 `.orch_<id>` 根互不污染；StructuredMemory 并发 save 无交错（锁） |
| S11 | 编排 resume | 中途快照 → resume | validated 语义正确决定续跑轮；DONE 任务不重跑 |
| S12 | 确定性退化 | 无 backend（legacy planner） | 单任务单轮完成，旧行为兼容 |

### 7.2 miniMaster 测试移植映射

| miniMaster 测试 | 去处 | 批次 | 取舍 |
|---|---|---|---|
| `test_state_machine.py` | `tests/orchestrator/test_state_machine.py` | ① | 全量 |
| `test_checklist.py` | `tests/orchestrator/test_checklist.py` | ① | 全量 |
| `test_memory.py`（WorkingMemory 部分） | `tests/orchestrator/test_working_memory.py` | ① | Executor 视图用例删除（D8），TOCTOU 竞态用例保留 |
| RetryArchive 用例 | `tests/orchestrator/test_retry_archive.py` | ① | compress_fn 缺省截断路径保留 |
| `test_harness_loop.py` | `tests/orchestrator/test_loop.py` | ① | FakeLLM → FakeBackend(ModelBackend) 改写 |
| `test_executor.py` | 拆：控制动作 → `tests/test_control_tools.py` | ② | 循环体本身不移植（D1）；no-tool 纠偏并入现有空答重问用例 |
| `test_action_policy.py` | `tests/test_policy.py` | ② | 全量（含 enforce 越权消息断言） |
| `test_guard.py` | `tests/test_repeat_guard.py` | ② | 全量（三规则 + reset） |
| `test_text_protocol.py` | `tests/test_local_openai_protocol.py` | ③ | FakeOpenAI 客户端替换真实 SDK 依赖 |
| `test_mcp.py` + `mcp_fake_server.py` | `tests/test_mcp.py` | ③ | 全量（真实子进程往返） |
| `test_live_context.py` | 摘用例并入 `tests/test_context.py` | ③ | 仅 tool_calls 配对边界（D9） |
| `test_json_tools.py` | `tests/test_util.py` | ① | 合并后实现 |
| `tests/fakes.py` | `tests/fakes.py` | ① | 适配 ModelBackend 协议 |

### 7.3 覆盖率门禁（批次⑤）

pytest-cov 不支持按路径分别 fail_under，采用：`coverage json` 输出 + `scripts/check_coverage.py` 断言——`agentmuster/orchestrator/** ≥ 90%`、全局 `≥ 75%`，CI 中 pytest 后执行。本地 `pytest --cov` 同口径。

### 7.4 真实模型验收（手动，批次④后）

本地 OpenAI 兼容端点跑 Layer 7：目标 8/8；对照 miniMaster 首轮 5/8 的历史，复跑发现缺陷走"缺陷 → 修复 → 回归测试"回流（沿用 miniMaster evidence.md 的证据链体裁，沉淀到 `docs/`）。

## 8. 风险与开放点

| # | 风险/开放点 | 对策 |
|---|---|---|
| R1 | MockBackend 结构化脚本脆弱（JSON 转义易错） | 测试工具函数 `json_response(obj)` 统一构造脚本项 |
| R2 | RunResult.status 新值 `blocked` 的下游兼容 | 批次② 同步清单：api 透传/监控徽标/eval 断言/aggregate 口径 |
| R3 | StructuredMemory 并发 save 交错 | 编排层互斥锁；S10 专项断言 |
| R4 | 监控页对新事件类型的渲染 | EventBus 无白名单（SSE 必达）；monitor_page.js 若按 type 定制渲染则批次① 补类型；验收项含 SSE 冒烟 |
| R5 | openai SDK 版本行为漂移 | extra `[llm]` pin `>=1.40,<3`；协议测试用 Fake 客户端隔离 |
| R6 | Windows CI 上 shell 工具语义差异 | 双 OS 矩阵正是为此；miniMaster 同矩阵先例可借 |
| O1 | 编排 resume × 子任务 checkpoint 的组合语义 | 首版：RUNNING 子任务整任务重跑；Layer 4 恢复评测扩展覆盖后再细化 |
| O2 | 角色模型路由的离线测试 | Config 克隆 + 双 MockBackend 注入（planner/validator 各自脚本） |
| O3 | `benchmarks/` 旧目录与 Layer 7 并存 | 本合并不动 benchmarks/；Layer 7 独立目录；README 分开表述 |

## 9. 验收清单（Definition of Done）

- [x] 五批全部合入，每批 CHANGELOG 条目 + 独立 commit 主题（b19ba1e/50ec4b2/e37496d/3d2a890/86f1fc3 + 批次⑤）
- [x] 全量测试绿：基座 272 项 + 移植/新增 76 项 = 348 项；Layer 7 首次真实 Ollama 实测驱动 1 项回归测试后 **349 项全绿**
- [x] miniMaster 84 项用例的对应物按 §7.2 全部落位或有记录的取舍（Executor 循环体不移植=D1、LiveContextTrimmer 组件不移植=D9、WorkingMemory 精简见执行期修订 1）
- [x] CI 双 OS 矩阵（ubuntu/windows × 3.11/3.12）+ 覆盖率门禁生效（编排层 ≥90% 实测 95.4%、全局 ≥75% 实测 80.2%）
- [ ] Layer 7 真实模型 8/8 + ablate 对照报告（手动，本地 OpenAI 兼容端点跑 `python -m agentmuster.eval.layer7_multiagent`）
- [x] README / ARCHITECTURE 呈现"单 Agent 底座 / 多智能体编排 / 七层评测"三层结构
- [x] 溯源：CHANGELOG 记录 miniMaster 快照 `24f4247` 与各批次移植范围
- [ ] GitHub 远端创建与推送（miniMaster 快照 + AgentMuster 主仓,待定方式）
