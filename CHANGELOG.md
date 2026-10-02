# Changelog

本项目的所有显著变更记录于此文件。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Added
- 评测 Layer 7 多智能体端到端基准(批次④,移植自 miniMaster eval/run_eval.py,快照 `24f4247`):8 个标准任务(hello/notes/calc/fizzbuzz/parallel-files/dep-chain/bugfix/codebase-grep)全走客观检查器——运行产物并验证(subprocess 断言/内容精确比对),不采信 Agent 自述;`--ablate guard,retry,budget,validator` 机制消融开关为"编排层价值"提供对照数字(真实模型手动跑:`python -m agentmuster.eval.layer7_multiagent --suite full`,不进 CI);指标含客观通过率/轮数/尝试/被拦截动作/重试/重规划/token/耗时,报告写 `eval/results/`(与工作区一同不入库)。**编排工作区语义修正**:同一编排内的子任务共享一个交付工作区(`.orch_<orch_id>/ws`)——批次① 的完全隔离会拆散 dep-chain 类 compound 目标,跨编排仍完全隔离;子任务内部事件(tool_call/denied 等)以 `sub` 标签并入编排事件流。测试 +7(检查器移植/消融映射/runner 冒烟),总数 341 → 348。
- 协议自适应 + 截断自愈 + MCP 接入(批次③,移植自 miniMaster 快照 `24f4247`):`LocalOpenAIBackend` 新增 NATIVE→TEXT_JSON 协议单向降级(端点拒绝 tools 的 HTTP 400 与"原生返回无工具调用且文本不可解析"双触发;降级后工具目录注入 system 消息、从文本回复解析动作,`util.parse_text_action` 支持 XML 工具标签/代码块/裸 JSON/首尾大括号四级候选)与 `finish_reason=length` 截断自愈(2×max_tokens 重试一次,上限 `max_tokens_ceiling=32768`;需显式配置 `model.local_openai.max_tokens`)。纯 urllib 实现,**未引入 openai SDK 依赖,核心零依赖叙事加强**(较 MERGE_DESIGN 原计划 `[llm]` extra 的改进)。`tools/mcp_client.py`:零依赖 stdio JSON-RPC 客户端(initialize 握手 / tools:list / tools:call,后台线程+队列超时等待兼容 Windows 管道),`MCPProxyTool` 把远端 inputSchema 零转换映射进 `ToolRegistry`(mcp_ 前缀,danger=WARN,参数校验走统一 SafetyGuard);`tools.mcp.server_cmd/timeout` 配置启用,失败降级纯内置工具并发出 `mcp_unavailable` 事件。上下文配对不变量回归(`test_context_pairing`,D9:固化"裁剪不得破坏 tool_calls/tool 配对")。死代码清理:删除零调用 `memory/retriever.py` 与根目录 4669 行生成产物 `generate_test_file.py`(ruff exclude 同步收窄),删除三个声明未生效的配置项 `context.budget_tokens/keep_last_tool_results/compressible_age`(`doctor`/`/health` 展示改指 `hard_limit_tokens`)。测试 +14(MCP 真实子进程往返 6、HTTP 桩协议状态机 6、上下文配对 2),总数 327 → 341。
- 安全防线第七道:重复/振荡动作 Guard + 控制工具 + 动作白名单(批次②,移植自 miniMaster 快照 `24f4247`):`safety/repeat_guard.py` 三重死循环检测(连续重复/窗口计数/周期振荡)并入 `SafetyGuard` 检查链(0. 动作白名单 → 1. 参数校验 → 2. 路径隔离 → 3. shell 名单 → 4. 去重缓存 → 4b. Guard → 5. HITL),去重缓存命中也计入指纹(`safety.repeat_guard.count_cache_hits`,默认开)以检测"反复重读"式刷步,命中即拦截并把策略切换引导语回灌给模型;每子任务独立 Guard 实例 + 任务启动时 reset,指纹状态天然隔离。控制工具 `tools/control_tools.py`(`submit_result(success, summary)` / `request_block(reason)`,不进默认注册表,由编排层为子任务装配):AgentHarness 在工具分发阶段识别并终止主循环,`RunResult` 新增 `control` 字段与 `blocked` 状态;编排层映射:submit(True)→DONE、submit(False)→FAILED(可重试)、request_block→BLOCKED,并代发 `subtask_control` 事件。`safety/policy.py` 角色动作白名单(ActionPolicy/PolicyViolation,Executor 白名单=工具注册表∪控制动作),经 `SafetyGuard.check(allowed_tools=...)` 生效,编排子任务经 `Task.extra["allow_tools"]` 按任务收窄。配置节 `safety.repeat_guard.*`。测试 +19(test_policy 4 移植、test_repeat_guard 7 移植+2 集成、test_control_tools 5、编排场景 S13/S14),总数 308 → 327。
- 多智能体编排层(批次①,移植自 miniMaster 快照 `24f4247`,设计见 `docs/MERGE_DESIGN.md`):`Orchestrator` 由一次性"分解→并行→聚合"升级为 Planner-Executor-Validator 多轮闭环——每轮「执行(依赖就绪任务可并行,每子任务仍由完全隔离根的独立 AgentHarness 执行)→ Validator 按 Completion Checklist 逐项验收 → missing_requirements 精确回流 Planner 增量重规划」;失败任务在轮内即时重入队(FAILED→PENDING 归档重注入),Retry Archive 把失败轨迹压缩为教训并注入重试上下文(`TaskInput.extra["retry_lessons"]` → 上下文 memory_block);全局 token 预算(`orchestrator.max_total_tokens`)超限将剩余 PENDING 任务整体转 BLOCKED;每任务收口/每轮收口写编排快照,`Orchestrator.resume(task_id)` 断点续跑(validated=True 从下一轮继续,False 重做本轮且 DONE 任务不重跑)。任务状态机(PENDING/RUNNING/DONE/FAILED/BLOCKED 迁移表硬约束,非法迁移抛 `IllegalTransitionError`)、结构化输出助手(`structured_complete`,后端无关,解析失败反馈重试环;`util.extract_json` 逐级候选解析)一并移植。新增包 `agentmuster/orchestrator/`(tasks/checklist/structured/planner/validator/working_memory/retry_archive/snapshot)与 `agent/prompts.py` 角色提示词。确定性退化兼容:未配置 LLM planner(默认 `orchestrator.planner_mode=deterministic`)时单任务单轮自动验收,旧用法(legacy `Callable[[str], list[dict]]` planner)经适配器保持原语义;LLM 模式经 `orchestrate --planner llm` 或配置启用,支持按角色模型路由(`orchestrator.roles.{planner,validator}.model/temperature`)。事件面新增 `orchestration_plan/round_start/round_end/validated/replan/resume/subtask_start/subtask_blocked/task_retry_scheduled/budget_exceeded/deps_invalid`,SSE 监控流直接可达。测试 +36 项(`tests/orchestrator/` 六文件:状态机/Checklist/结构化输出/角色视图记忆/Retry Archive + S1-S12 多轮闭环场景),总数 272 → 308。
- Layer 6b 裸模型基线对照(`mycoder/eval/raw_baseline.py`):固定模型与 `benchmarks/real_tasks.json` 任务集,只改"有没有 harness"——`single_shot`(单次调用,目标与 setup 文件内联,无工具循环)与 `naive_loop`(朴素 tool-calling 循环,刻意不用上下文治理/结构化记忆/checkpoint/安全审批链/去重/工件系统,仅保留 Workspace 文件边界;`shell_exec`/`memory_query` 因依赖审批链与记忆系统不暴露)两条裸基线臂。复用 Layer 6 同一套硬断言(`EvalRunner._check_expect`)与 token/成本/耗时口径;存在 Layer 6 的 `real_report.json` 时报告 `comparison` 字段自动并排三臂对照。`eval --suite real_baseline` 独立可跑,配置节 `eval.real_baseline`;mock 后端下优雅跳过。新增 `tests/test_real_baseline.py`(6 项离线用例;17 → 18 个测试文件,测试总数 262 → 268)。首次三臂实测(硬断言口径,qwen3.5:2b):single_shot 1/4、naive_loop 3/4、harness 4/4。
- 空终答温和重问(`harness.empty_answer_nudges`,默认 1,0 = 关闭):模型返回"无工具调用且无内容"的空终答时不再静默按完成处理,而是注入一条用户提醒(要求通过 file_edit/file_write 落盘后给出终答)继续循环,给小模型补交机会;轮结构新增可选 `user` 位,checkpoint 序列化向后兼容。测试总数 268 → 272(test_harness 15 → 18,新增触发/预算耗尽/可关闭 3 项;test_real_baseline 6 → 7,见下条 suite 不清空修复)。
- Web 监控页后端自由切换 + 一键双跑对照:`POST /api/run` 新增可选 `backend` 字段(三档:跟随配置/mock/local_openai;携带 script 仍锁定 Mock);新增 `POST /api/compare` 同一目标自动提交 mock+ollama 两臂任务并返回 `compare_id`;任务快照与列表透出 `backend/arm/compare_group`;监控页新增「执行后端」选择、「▶ 双跑对比」按钮与两臂指标并排对比表。设计记录见 `docs/WEB_BACKEND_SWITCH.md`。
- 环境工程化：仓库内置 Conda prefix 独立环境 `.conda/`(Python 3.11,由 Anaconda 管理,`.gitignore` 排除不入库),新增 `environment.yml` 与 `requirements-{dev,api,vector,project}.txt` 分拆清单;一条 `conda env create -p .conda -f environment.yml` 即可在任意机器完整重建。
- 企业化改造：新增 MIT LICENSE、Docker Compose（Ollama + FastAPI）、82 条检索评测集、Layer 6 Ollama 真实任务 + LLM-as-judge、Hashing/FastEmbed 对照入口，以及本地 vendored Vue 3 运行监控页。
- `LocalOpenAIBackend` 修复内部工具调用到 OpenAI 标准 `type/function` 格式的转换，兼容 Ollama 多轮工具调用。

### Changed
- **破坏性改名** `mycoder` → `agentmuster`(批次① c1,机械重命名零逻辑变更):包目录/全部 import/文档/打包配置统一改名;console script 主命令 `agentmuster`(保留 `mycoder` 兼容别名);默认工件路径 `.mycoder/` → `.agentmuster/`;`requires-python` 与 ruff/mypy 工具链目标升至 3.11;ruff exclude 补 `.mycoder`/`.pytest_tmp` 运行期产物目录;顺手修复改名撑长的 E501 与存量 mypy method-assign 报错。CHANGELOG 历史条目保持原名不改写。
- 文档系统性审计(README/TESTING/OUTLINE/FINAL_SUMMARY/LEARNING_GUIDE):环境说明统一改为项目内置 `.conda` 环境,清除 ML2/base 及机器专属路径(`D:\ANACONDA\...`、`D:\DeepSeek Harness\...`)残留;测试统计修正为 **258 项/17 个文件**并为各文件标注实测用例数(test_safety 27→70、test_eval 14→18、test_models 14→15);benchmark 数据口径修正为手写任务 26 个 + 固定 seed 冻结基准 42 个;检索基准按 82 条查询的实测 recall/MRR 结果更新;LEARNING_GUIDE 新增「环境准备」与「模块关系一览」章节,补齐 Layer 6/7、`--suite real|embedder`、`GET /api/runs` 与 Vue 监控页等此前缺失的能力描述。

### Fixed
- `EvalRunner.run_suite` 对 `real` / `real_baseline` 套件不再整体 `_reset` 输出目录:此前同一 `--output` 目录先跑 Layer 6 再跑 Layer 6b 会清掉先跑完的 `real_report.json`,三臂对照依赖两份报告共存。
- harness 日志初始化此前直接 `FileHandler(".mycoder/harness.log")`,任何全新环境(新机器克隆、Docker 容器)下父目录不存在都会 `FileNotFoundError`;现于打开前 `mkdir(parents=True)`。
- `tests/test_performance.py` 的 `RESULTS` 空字典补显式类型注解,保证最小依赖环境下 `mypy` 可通过。
- `monitor_page` 提交体此前总是携带空 `script`,导致页面任务无条件走 MockBackend;现改为仅填写脚本才携带,配合「执行后端」选择语义修正。
- `tools/sandbox.py` 工作区指纹遍历由 `rglob('*') 先全量展开再过滤` 改为 `os.walk` 进入前剪枝:修复工作区落在大型项目根(含 .conda/.mimosa 等数万条目)时每次 checkpoint 卡顿一个数量级的性能缺陷,过滤语义不变。
- `examples/giant_test.py`：修复生成模板转义残留的 `%%` 双百分号（非法 Python 语法），恢复为 `%`。

### Removed
- 移除 GitHub Actions CI(`.github/workflows/ci.yml`,含 lint/mypy/test 矩阵/docker-build 四个 job):远程质量门暂时下线,项目本地运行与 Docker 部署不受影响;质量检查改以本地 `ruff check` / `mypy` / `pytest` 为准(见 `docs/TESTING.md`「质量门(本地执行)」)。

### Added
- `feat(observability)`: 新增 `observability/tracing.py`，零依赖 `Span`/`Tracer` 导出 OTLP 风格 `trace.json`；安装 `opentelemetry-api` 时自动桥接；`harness.build` 的 `on_event` 回调同时驱动默认 Tracer 与调用方事件总线；`logging.format: text|json` 结构化日志；`artifacts` 报告增加耗时时间线与成本小节。
- `feat(memory)`: 新增 `memory/vectors.py`，`EmbeddingProvider` + `HashingEmbedder`（零依赖确定性字符 n-gram 哈希，默认）+ `FastEmbedEmbedder`（可选 bge-small）；`VectorIndex`（余弦 + 持久化）+ 纯 Python `BM25`；混合检索 `score = α·cosine + (1-α)·bm25`；`StructuredMemory.search()` 支持 `substring`/`vector`/`hybrid` 三种模式（默认 substring 向后兼容）。
- `feat(eval)`: 评测升级为五层，新增 Layer 5 检索召回（`benchmarks/retrieval.json`，6 条同义改写查询，hybrid recall@3=100% vs substring=0%）；`eval --suite retrieval` 独立可跑。
- `feat(api)`: 新增 FastAPI + SSE 服务 `api/event_bus.py`（`TaskEventBus`）+ `api/fastapi_server.py`（`POST /api/run`、`GET /api/run/{id}`、`GET /api/run/{id}/events` SSE 含 `done` 哨兵 + 15s 心跳、`GET /api/artifacts/{id}/{name}`、`/health`、零构建 vanilla JS 实时轨迹页）；`cli serve --impl stdlib|fastapi`（默认 stdlib 保持零依赖）；`api` 依赖组可选。
- `feat(agent)`: 新增 `agent/orchestrator.py`，`Orchestrator` 由 `Planner`（默认确定性退化分解，可注入 LLM JSON 分解）产出子任务，各子任务由完全隔离根的子 `AgentHarness` 经 `ThreadPoolExecutor` 并行执行，失败降级标记 `failed` 不阻断整体，产出 `orchestration.json`，经 `on_event` 发出 `orchestration_start`/`subtask_end`/`orchestration_end`；`config agent.orchestrator.{enabled,max_workers}`（默认关闭）。
- `feat(cli)`: 新增 `orchestrate` 子命令（`--goal`/`--task-id`/`--config`/`--workspace`/`--hitl-policy`/`--backend`/`--max-workers`），把复杂目标分解为子任务并行编排执行。
- `feat(deps)`: `pyproject` optional-dependencies 分组 `api`/`vector`/`otel`/`dev`，核心保持仅依赖 PyYAML 的零依赖。

### Changed
- `refactor(config)`: `config.py` DEFAULT 补齐 `model.local_openai.*`、`model.pricing`、`context.summarizer`、`memory.retrieval.mode/alpha/embedder`、`logging.format`、`observability.enabled`、`agent.orchestrator.*`。
- `refactor(memory)`: `memory/store.py` 接入 `vectors.py` 检索模式切换，`search()` 新增 `mode` 参数。
- `refactor(eval)`: `eval/runner.py` 扩展 Layer 5 retrieval 评测与 A/B 对照框架；`tests/test_eval.py` 覆盖五层。
- `refactor(agent)`: `agent/harness.py` 注入最小侵入 `on_event`；`agent/__init__.py` 导出 `Orchestrator`；`api/__init__.py` 增加 `impl` 开关。
- `test`: 新增 `tests/test_observability.py`(7)/`test_vectors.py`(11)/`test_api.py`(3)/`test_orchestrator.py`(4)/`test_cost.py`(5)/`test_backend.py`(9)；全量测试升至 **206 项 / 16 个测试文件**。

### Docs
- 新增 `docs/IMPROVEMENT_PLAN.md`：企业化改造整体计划（背景评估、分期范围、验收标准、结果记录）。
- 新增 `CHANGELOG.md`（本文件）：与 conventional commits 提交一一对应。
- `docs/IMPROVEMENT_PLAN.md`：补齐 Phase 3–7 落地状态与结果记录，全部标记已完成；评测口径统一为五层 / 206 项。
- `README.md` / `docs/ARCHITECTURE.md` / `docs/TESTING.md` / `docs/OUTLINE.md` / `docs/FINAL_SUMMARY.md` / `docs/LEARNING_GUIDE.md`：同步可观测性、向量记忆、五层评测、FastAPI+SSE、子代理编排、`orchestrate` CLI、成本计量、依赖分组等新能力；测试计数统一为 206 项 / 16 文件；去除机器专属路径。
