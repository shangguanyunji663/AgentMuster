# 文档一致性审计报告（2026-10-04）

> **范围**：全仓库代码（`agentmuster/` 66 个 .py + tests/examples/scripts）与全部项目文档（README、CHANGELOG、`docs/*.md` 共 12 份）。
> **原则**：以代码实际实现为唯一事实来源；文档间矛盾一律按代码修正并注明原因；仅改受影响部分，保留原有结构、术语与内部链接/锚点/目录。
> **结论**：共更新 **12 份文档 + 1 处代码 docstring**；核验后内部链接、目录与锚点全部有效。

---

## 一、代码事实基线（本次审计的判定依据）

| 事实项 | 代码实测值 | 来源 |
| --- | --- | --- |
| 包名 / console script | `agentmuster`（保留 `mycoder` 兼容别名） | `pyproject.toml:6,33-34` |
| Python 版本 | `requires-python>=3.11` | `pyproject.toml:10` |
| 测试用例 / 文件 | **349 项 / 31 个文件**（25 个 `tests/test_*.py` + 6 个 `tests/orchestrator/test_*.py`） | `pytest --collect-only` 实测 |
| 内置工具 | 7 个：`file_read/file_write/file_edit/file_list/grep_search/shell_exec/memory_query`（+ 控制工具 `submit_result/request_block` 不进默认注册表） | `tools/__init__.py`、`tools/control_tools.py` |
| 安全链检查点 | 7 道（动作白名单→参数校验→路径隔离→shell 名单→去重→重复/振荡 Guard→HITL），脱敏为输出侧后处理 | `safety/guard.py:148-211` |
| 上下文裁剪触发 | 由 `hard_limit_tokens` + `keep_last_turns` 驱动；`context.budget_tokens` **不在 DEFAULT**，仅供评测运行器写入 / stdlib `/health` 透出 | `context/manager.py:107-168`、`config.py:45-50` |
| 编排工作区语义 | 同一编排内子任务**共享交付工作区** `.orch_<id>/ws`；记忆/断点/工件按子任务隔离 | `agent/orchestrator.py:400-411` |
| CI 状态 | **已恢复**：`.github/workflows/ci.yml` 双 OS（ubuntu/windows）× 3.11/3.12 | `.github/workflows/ci.yml` |
| 已删除文件 | `memory/retriever.py`、根目录 `generate_test_file.py` | 批次③ 死代码清理 |
| Layer 7 编号 | 文档统一为「多智能体端到端基准」；嵌入器对照改称「嵌入器对照（suite `embedder`）」 | `eval/runner.py:697` vs `eval/layer7_multiagent.py` |

---

## 二、被更新文档清单与变更摘要

### 1. `README.md`
- 徽章测试数 `348 passed` → **`349 passed`**；正文各处 `272 项` → `349 项`，`19 个文件` → `31 个文件`。
- 修复路径笔误 `agent/agent/orchestrator.py` → `agentmuster/agent/orchestrator.py`。
- 可选依赖组名 `agentmuster-harness[api|vector|otel|dev]` → **`agentmuster[...]`**（与 `pyproject` 包名一致）。
- `doctor` 输出示例 `上下文预算: 4000 tokens` → 实际字段 `上下文硬上限: 6000 tokens`。
- **安全链口径统一**：第 27 行与第 275 行原本「七道防线 / 六道防线」互相矛盾 → 统一为 **七道检查点**（与 `SafetyGuard.check()` 编号链一致），脱敏单列。
- 编排一节「完全独立工作区/记忆/断点/工件根」→ 修正为「同一编排内共享交付工作区 + 记忆/断点/工件按子任务隔离」。
- 配置表 `context.budget_tokens`（软预算 4000）→ 改为 `hard_limit_tokens / keep_last_turns / max_file_content_chars / summarizer`，并注明 `budget_tokens` 非 DEFAULT、不参与裁剪触发。
- 文档地图补入 `docs/MERGE_DESIGN.md`、`docs/AgentMuster学习指南.md`；TESTING 描述更新为「CI + 本地质量门」。

### 2. `CHANGELOG.md`
- 修正批次③ 条目：`context.budget_tokens` **并未删除**（仍由 `EvalRunner._cfg_for()` 写入、stdlib `/health` 透出），实际只删了 `keep_last_tool_results`/`compressible_age`，且仅 `doctor` 与 FastAPI `/health` 改指 `hard_limit_tokens`。
- 为 `Removed` 的「移除 GitHub Actions CI」条目补**后续状态更正**：批次⑤ 已恢复 CI（原文与当前代码矛盾）。

### 3. `docs/ARCHITECTURE.md`
- 重写「Orchestrator」小节：`decompose()`/一次性分解/完全隔离 → `run(goal)` 多轮 Planner-Validator 闭环、共享交付工作区、`resume()`、完整事件集。
- `SafetyGuard.check(tool, params)` → `check(tool, params, allowed_tools=None)`；安全层描述补「动作白名单 / 重复振荡 Guard」。
- `AgentHarness.build` 签名补全默认参数。
- 巨型文件说明：删除已失效的「生成方式 `python generate_test_file.py`」，注明脚本已删。

### 4. `docs/TESTING.md`
- 测试计数 `272 项 / 18 文件` → **`349 项 / 31 文件`**；重写「测试用例统计」表（补齐 13 个遗漏文件、`test_models` 15→16）。
- **Layer 7 术语消歧**：原「Layer 7 = 嵌入器对照」与 README/CHANGELOG 的「Layer 7 = 多智能体基准」冲突 → 拆分并加术语注。
- 「质量门(本地执行)」→ **「质量门(CI + 本地执行)」**：更正「项目当前不依赖远端 CI」的过时表述。
- 移除机器专属路径 `D:\PythonProject\agentmuster\.conda` → `<项目根>/.conda`；`generate_test_file.py` 重新生成指引改为「已删除」。
- `orchestrator` 覆盖描述更新为多轮闭环/状态机/Retry Archive。

### 5. `docs/OUTLINE.md`
- Python `3.10+` → **`3.11+`**；核心代码 `~35 个` → **`66 个`**。
- 文件清单重写：删除 `memory/retriever.py`，补 `vectors.py`、`policy.py`、`repeat_guard.py`、`control_tools.py`、`mcp_client.py`、`orchestrator.py`、`prompts.py`、`observability/`、`orchestrator/` 包、`layer7_multiagent.py` 等。
- 测试清单 `18 文件 / 272 用例` → `31 文件 / 349 用例`；示例区删除 `generate_test_file.py`、补 `kb_lora/` 与 `scripts/`。
- `summarizer` 补 `LLMSummarizer`；`agentmuster-harness[vector]` → `agentmuster[vector]`；未来工作中已完成的「接入 LLM Planner」移出。

### 6. `docs/FINAL_SUMMARY.md`
- 头部 `Python 3.10+` → `3.11+`；测试结果 `272 / 18 文件` → **`349 / 31 文件`**（基线 347 passed + 2 skipped）。
- 目录树重写：删 `generate_test_file.py`、`retriever.py`；补 `orchestrator/` 包、`prompts.py`、`policy.py`、`repeat_guard.py`、`layer7_multiagent.py` 等；测试树补齐 31 文件。
- 评测架构 `5 层` → **七层**（补 Layer 6/6b/7）；Layer 2 基线 `budget=1_000_000` → 实测 `10_000_000`。
- 配置表 `context.budget_tokens = 4000` → 注明非 DEFAULT、不触发裁剪；巨型文件生成方式改为「已删除」。
- 文档目录补 `MERGE_DESIGN.md`、`AgentMuster学习指南.md`；机器专属路径改为 `<项目根>`。

### 7. `docs/EVAL_HARDENING.md`
- 顶部新增「**当前基线（2026-10 复核）**」：说明第 1–2 章「现状/根因」为**改造前**旧口径（tasks 12 / retrieval 6），并给出改造后真实数据（26+42 任务、82 查询、payload 15+8），消除与当前代码的矛盾。

### 8. `docs/IMPROVEMENT_PLAN.md`
- 状态注记重写：CI **已恢复**（双 OS 矩阵 + 覆盖率门禁），并说明 Phase 1「3.10–3.12 矩阵」、Phase 6「完全独立子工作区」为历史记录。
- 测试统计链补终值 **349 项 / 31 文件**；Phase 6 结果记录的「完全独立工作区/记忆/断点/工件根」改为共享交付工作区表述。

### 9. `docs/WEB_BACKEND_SWITCH.md`
- 「设计时 258 项，现为 272 项」→ 注明后续经 miniMaster 合并与 Layer 7 实测增至 **349 项**。

### 10. `docs/MERGE_DESIGN.md`
- DoD `348 项` → **`349 项全绿`**；`memory/structured_memory.py` → 实际 `memory/store.py`。
- 死代码清理条目更正：`context.budget_tokens` 经核查仍在生效，予以保留。

### 11. `docs/LEARNING_GUIDE.md`（旧版学习指南）
- 全文测试计数 `272` → **`349`**，`18 个测试文件` → `31 个`；离线基线 `270 passed + 2 skipped` → `347 passed + 2 skipped`。
- Python 版本 `3.11（兼容 3.10+）` → `requires-python>=3.11`；`agentmuster-harness[api]` → `agentmuster[api]`。
- **配置章节事实修正**：`context.budget_tokens=4000（超了触发折叠）` → 更正为「不在 DEFAULT、不触发裁剪」；示例改用 `hard_limit_tokens`，并修正 `Config.load()` 为类方法的用法。
- `retriever.py` 章节改写为「已移除，逻辑归并至 `StructuredMemory.has_fresh_summary()`」；检索评测示例改用真实 API `mem.rank(...)`。
- 第 12 章（编排）加「⚠ 代码现状」横幅，说明 `SubTask/decompose/完全隔离` 为批次① 前旧实现。
- 测试索引表补齐 31 文件；Layer 7 标签由「嵌入器对照」改称并加注与多智能体基准的编号重叠；机器专属路径改为 `<repo>`。

### 12. `docs/AgentMuster学习指南.md`（新版深度学习指南）
- 测试文件数 `24 文件` → **`31 文件`**（实测 25+6）。
- 可选依赖组 `agentmuster-harness[api]` → `agentmuster[api]`。
- **术语统一**：全文「九检查点」→ **「七检查点」**（与代码编号链及 README 一致），并修正第 4072 行枚举。
- 附录 B「已知不一致」更新：第 1–6 项文档层出入标注为**已修正**，第 7–12 项保留为代码层待办。

### 13. `agentmuster/agent/orchestrator.py`（代码 docstring，文档性质修正）
- 模块 docstring「每个子任务仍由**完全隔离根**的独立 AgentHarness 执行（工作区/记忆/断点/工件互不污染）」与批次④ 修正后的代码矛盾 → 更正为「同一编排内子任务**共享交付工作区**，记忆/断点/工件按子任务隔离，跨编排完全隔离」。

---

## 三、跨文档一致性核验

| 概念 | 统一后口径 | 涉及文档 |
| --- | --- | --- |
| 测试总量 | 349 项 / 31 文件 | README、CHANGELOG、TESTING、OUTLINE、FINAL_SUMMARY、两版学习指南 |
| 安全链 | 七道检查点（+ 输出侧脱敏） | README、AgentMuster学习指南、ARCHITECTURE |
| 包名 / 安装 | `agentmuster` / `agentmuster[extras]` | README、OUTLINE、两版学习指南 |
| Layer 7 | 多智能体端到端基准；嵌入器对照单列 | README、TESTING、CHANGELOG、两版学习指南 |
| 编排工作区 | 共享交付工作区（记忆/断点/工件隔离） | README、ARCHITECTURE、IMPROVEMENT_PLAN、两版学习指南、代码 docstring |
| CI | 双 OS 矩阵已恢复 | README、TESTING、IMPROVEMENT_PLAN、CHANGELOG |

**遗留（非本次文档范围，代码层待办，已在 `AgentMuster学习指南.md` 附录 B 记录）**：`subtask_end` 重复发射、确定性模式下空终答可能被标 DONE、冻结数据 `wrong_hit` 播种错位、`test_loop.py` S9 缺号、角色层 `_emit` 未抑制异常、`event_bus.drop()` 未被调用。
