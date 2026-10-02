# AgentMuster 学习指南 — 从零吃透一个本地 Coding Agent Harness（单 Agent 底座 × 多智能体编排 × 七层评测）

> 本文档按照「如果你要从头写这个项目，你会怎么思考和编码」的顺序组织。它不是一份 API 清单，而是一份引导式蓝图：先讲清楚「这个项目解决什么问题、为什么这样设计」（背景与架构）、「为什么选这些技术」（选型理由）、「每一类故障由哪个机制兜底」（核心流程），然后**逐模块贴源码逐段精读**（12 站走读，所有代码摘录均带真实行号），最后落到「怎么在简历和面试里把它讲透」（求职专题）。
>
> **读者定位**：准备投递 Agent 应用开发岗位的工程师/学生，有 Python 基础，读过（或写过）一个 LLM 调用脚本，但不一定系统接触过 Harness、工具治理、多智能体编排这些工程概念。
>
> **正确性基准**：以仓库当前 `main` 分支（`f2aba60`）为准——349 项 pytest 全绿、CI 双 OS 矩阵通过、全局覆盖率 80.4% / 编排层 94.9%。文中代码摘录为 `main` 分支真实源码（行号一致，个别为讲清主干做了删节，删节处标注 `…`），完整行为以源码为准。
>
> **与既有文档的关系**：仓库原有的 `docs/LEARNING_GUIDE.md` 写作于 miniMaster 合并之前，不含编排层、安全增强、MCP、协议自愈、Layer 7 与 CI——本文档是覆盖合并后全量现状的完整版，冲突处以本文档与源码为准。

***

# 如何使用本指南（先读这一页）

> 本节是整份指南的「导航页」：先用 2 分钟确定适合你的学习路径，再按路径跳读；任何时候迷路了，回到本页的目录或文末的自测清单即可。

## 四类读者，四条路径

| 你是… | 建议路径 | 预计投入 | 怎么走 |
| --- | --- | --- | --- |
| 想先看看效果 | 路径 A · 快速体验 | 约 30 分钟 | 读 1.1 问题表 → 按第七部分 7.1/7.2 把 demo 跑起来 → 打开监控页看一次双跑对比。其余章节用到再回来查。 |
| 零基础系统学习 | 路径 B · 全程跟学 | 2~3 周 | 第零部分补齐概念 → 第一~五部分建立全局 → 按第六部分 12 站顺序通读（每站对照源码完成「练一练」）→ 第八部分看测试怎么锁行为。 |
| 有经验、查特定专题 | 路径 C · 专题跳读 | 按需 | 用下方「专题地图」直接定位；每站开头的「为什么先写它」都可独立成篇。 |
| 准备面试 / 写简历 | 路径 D · 求职冲刺 | 3~5 天 | 先走一遍路径 A 建立体感 → 精读第 8、9 两站（主循环与编排，全书核心）→ 直奔第十部分背答案 → 用附录 C 自测清单查漏。 |

**路径 C · 专题地图**（五个最受关注的话题，各自的最短阅读路线）：

- **多智能体编排**：1.2 演进史 → 5.5 多轮闭环 → 第 9 站（全书核心）→ 5.8 / 第 11 站 Layer 7 消融
- **安全与工具治理**：2.1 设计哲学 → 5.2 安全链全流程 → 第 3 站 → 第 4 站 → 8.3 CI 跨平台修复链
- **上下文与记忆**：1.1 故障表 → 5.3 裁剪决策树 → 第 5 站 → 第 6 站 → 第 11 站 Layer 2/3/5
- **评测体系**：2.1「如实度量」→ 5.8 评测数据流 → 第 11 站 → 10.4 面试题「怎么证明 harness 有用」
- **工程质量**：第四部分目录 → 第八部分测试与 CI → 附录 B 已知不一致清单 → 附录 E 测试精读
- **面试白板热身**：附录 F 六道现场写代码题（全部取材自本项目核心代码）

## 每一站的固定结构

第六部分的每一站都按同一结构展开，便于查阅与跳读：

1. **为什么先写它** —— 该站在依赖图中的位置与设计动机；
2. **关键实现** —— 逐段贴源码（真实行号）+ 每段在讲什么、为什么这么写；
3. **动手试一试** —— 可直接复制运行的命令与预期输出；
4. **常见易错点** —— 最常踩的坑；
5. **练一练** —— 递进练习，验证「真的学会了」。

## 全书总目录

| 部分 | 内容 | 回答的问题 |
| --- | --- | --- |
| 第零部分 | 预备知识与术语表 | 「这个词是什么意思？」 |
| 第一部分 | 项目背景与目标 | 「它解决什么问题？从哪来？」 |
| 第二部分 | 架构设计思路 | 「为什么这样设计？」 |
| 第三部分 | 技术栈与选型理由 | 「为什么选这些技术？」 |
| 第四部分 | 目录结构总览 | 「代码都在哪？谁依赖谁？」 |
| 第五部分 | 核心流程（时序级拆解，逐行对照源码） | 「一次任务/一次工具调用/一轮编排到底发生了什么？」 |
| 第六部分 | 逐模块源码精读（12 站） | 「每一站具体怎么写？源码长什么样？」 |
| 第七部分 | 使用方式实操 | 「怎么跑起来、怎么配、怎么评测？」 |
| 第八部分 | 测试与质量保障 | 「349 项测试怎么组织？CI 怎么把门？」 |
| 第九部分 | 设计模式回顾与一页总图 | 「读完之后怎么把知识收拢？」 |
| 第十部分 | 简历展示与面试准备 | 「怎么把它讲成 offer？」 |
| 附录 A~H | 事件全集 / 已知不一致 / 自测清单 / FAQ / 测试精读 / 白板题 / 速记卡 / 文件索引 | 「细节去哪查？学没学会怎么验证？」 |

## 三条使用建议

1. **先跑通，再阅读**：环境搭建不超过十分钟（第七部分），跑通后读每一站都能随手用「动手试一试」验证理解，比纯阅读快得多。
2. **对照源码读**：本文所有代码片段都标注了真实行号；读懂一个站的标准是「能合上文档说出这段代码为什么存在」。
3. **把「已知不一致」当镜子**：附录 B 列出了文档与代码的每一处出入。能独立把这些出入找出来并解释成因，说明你真的读懂了这套系统——这本身也是高级别的面试谈资。

***

# 第零部分：预备知识与术语表（缺概念从这里开始）

## 0.1 预备知识自检清单

| 领域 | 需要掌握到… | 不会怎么办 |
| --- | --- | --- |
| Python | 函数、类、`dataclass`、`Enum`、`dict` 深浅拷贝、`concurrent.futures`、装饰器上下文（`contextlib`）；能读懂类型注解 `list[str] \| None` | 本文用到新语法时会就地给一句解释 |
| 命令行 | 会 `cd`、`pip`、`python -m` | 第七部分每条命令都有注释 |
| HTTP / JSON | 知道「请求-响应」「状态码」「JSON Schema 是校验工具」「SSE 是服务器单向推流」 | 第 3 站与第 10 站开头各有 3 分钟版背景 |
| LLM API | 用过任意聊天产品；知道 chat/completions 的 messages/tools 大致形态 | 第 2 站从「后端抽象为什么存在」讲起 |
| pytest | 知道「测试函数 + assert」即可 | 第八部分从测试策略讲起，不要求先会 |

## 0.2 十分钟概念速成

每个概念按「一句话定义 → 在本项目长什么样 → 详见」三段展开：

- **Agent（智能体）**：能「读目标 → 决策 → 调工具 → 产出」的软件角色。本项目里一个 Agent = 一个 `AgentHarness` 实例 + 它独占的模型后端/工具集/记忆/断点。→ 第 8 站。
- **Harness（运行底座）**：把「模型很聪明但什么都不会」变成「能干活、可观测、可恢复」的那层工程外壳：主循环、工具执行、上下文管理、安全边界、工件沉淀。AgentMuster 本质上就是一个 Harness 项目——`agent/harness.py` 的模块 docstring 自述：**「主循环本身不关心模型是不是真的『聪明』，它只保证：确定性、可观测、可恢复。」**→ 1.1、第 8 站。
- **工具循环（tool-calling loop）**：模型每轮可以「说话」或「点菜」（发起工具调用）；Harness 执行工具、把结果回填、再问模型，直到给出终答。单次调用 → 工具循环 → 完整 Harness 是三层能力递进。→ 5.1、10.4。
- **Function Calling**：让模型从白名单里挑一个函数并给出参数，由**代码**执行。模型只点菜不下厨；参数格式由 JSON Schema 约束。→ 第 2、3 站。
- **MCP（Model Context Protocol）**：把「工具」封装成跨进程标准服务的协议（JSON-RPC 2.0 over stdio）。本项目用零依赖 stdio 客户端接入外部 MCP server，远端工具零转换注册进本地注册表。→ 第 3 站 3.6。
- **SFT / QLoRA**：监督微调（拿「指令→理想输出」样本训模型）；QLoRA 是 4-bit 量化底座 + 低秩适配器的省显微调方案。本项目不训练模型，但内置两条数据/微调支线：任务成功自动采集 SFT 样本、`kb_lora/` 企业知识库微调线。→ 第 12 站。
- **BM25**：经典词频打分算法：查询词在某文档出现越多、该词越稀有，得分越高。可解释、零成本。→ 第 6 站 6.3。
- **嵌入 / 向量检索**：把文字压成向量，语义相近则余弦相似度高，能命中「登入 ↔ 登录」这类词面不重叠的表达。本项目默认用零依赖的字符 n-gram 哈希嵌入器，可选升级真实语义模型 bge-small。→ 第 6 站 6.3。
- **混合检索（hybrid）**：稠密向量 + 稀疏 BM25 双路召回，`score = α·cosine + (1-α)·bm25` 融合，同义改写召回显著优于任一单路（recall@3 从 28% 提到 63%）。→ 5.8、第 11 站。
- **SSE（Server-Sent Events）**：服务器向浏览器单向持续推送文本事件的 HTTP 协议。本项目用它把每一步工具调用实时推到监控页。→ 第 10 站。
- **HITL（Human-In-The-Loop）**：高风险动作先经人工审批再执行。本项目 `shell_exec` 默认走 `prompt/allow/deny` 三档审批策略。→ 5.2、第 4 站。
- **状态机**：用「有限状态 + 允许的转移表」硬约束业务流程。编排层的任务五状态（PENDING/RUNNING/DONE/FAILED/BLOCKED）非法迁移直接抛 `IllegalTransitionError`，防 LLM 输出把系统带偏。→ 5.5。
- **Checkpoint / Resume**：把执行现场（上下文、后端游标、工作区指纹、指标）周期性落盘，中断后从断点续跑；恢复前先比对工作区 SHA256 指纹识别「外部漂移」。→ 5.4、第 7 站。
- **A/B 对照与消融**：固定任务与数据、只改一个开关，看指标变化——A/B 回答「这个系统有没有用」，消融（ablation）回答「系统里哪个机制贡献最大」。本项目的评测体系把这两种对照做成了基建。→ 5.8、第 11 站。
- **LLM-as-judge**：让另一个模型当评委对产出打分。本项目评委只做否决项，硬断言（文件存在/内容比对/真实执行）才是主判定，防止「评委掩盖硬失败」。→ 第 11 站 11.4。
- **确定性回放（Mock 轨迹）**：把「模型每轮说什么」写成脚本离线回放，同一输入必得同一输出——评测从此可复现、可进 CI、不花一分钱 API 费。→ 第 2 站 2.2。
- **数据飞轮**：Agent 干活 → 轨迹与结果沉淀为训练样本 → 微调出更适配的模型 → 接回 Agent。本项目用 `sft_collector` + `kb_lora` 把这个环闭合了。→ 第 12 站。

## 0.3 术语表

按主题分组；每条给出本项目内的标准叫法（全文统一按此书写，检索时直接搜中文词即可）。

**主循环与状态**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 主循环 | `agent/harness.py` 的 `_run()` | 组装上下文→调模型→执行工具→沉淀记忆→落断点，直到终答 |
| 步（step） | `Step`（state.py） | 一次「模型响应 + 其工具调用执行」的原子单元，`max_steps` 默认 30 |
| 轮（turn） | `ContextManager.raw_turns` | `{assistant, tool[], user?}` 三元组，上下文裁剪的原子粒度 |
| 空终答温和重问 | `harness.empty_answer_nudges`（默认 1） | 模型交白卷时注入提醒再给一次机会，而不是静默完成 |
| 控制信号 | `_control_signal` | 控制工具触发的本轮终态信号（submit_result / request_block） |
| 终态 | `RunResult.status` | completed / max_steps / error / interrupted / **blocked** 五种 |

**上下文与记忆**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 软预算 / 硬限额 | `context.budget_tokens` / `hard_limit_tokens`（6000） | 软预算只用于指标合规统计；硬限额由裁剪链强制保证 |
| 三级裁剪 | fold_old_turns → drop_stale_turns → truncate_long_content | 折叠旧轮 → 只留最近 1 轮 → 强制截断最长消息 |
| 配对不变量 | `tests/test_context_pairing.py` | assistant.tool_calls 与 tool 消息必须原子成对，裁剪不得拆散（拆散=API 400） |
| 三层记忆 | `memory/store.py` | 任务摘要 / 文件摘要（SHA256 去重）/ 关联记忆（任务↔文件↔父任务） |
| follow-up 注入 | `followup_context()` | 子任务自动携带父任务摘要与相关文件摘要，重读归零 |
| 检索三模式 | `memory.retrieval.mode` | substring（默认）/ vector（哈希嵌入）/ hybrid（向量+BM25，α 融合） |

**安全**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 安全链 | `SafetyGuard.check()` | 白名单→Schema→沙箱→shell 名单→去重→振荡 Guard→HITL 的检查点链 |
| 路径沙箱 | `tools/sandbox.py` 的 `Workspace.resolve()` | 空字节/反斜杠归一/绝对路径/符号链接/commonpath 五步拦截 |
| 去重缓存 | `guard._dedup` | 同参数重复调用短路由返回缓存（读类计命中、写类计跳过） |
| 重复/振荡 Guard | `safety/repeat_guard.py` | 连续重复/窗口计数/周期振荡三重检测死循环 |
| 动作白名单 | `safety/policy.py` | 每类角色只允许指定动作，越权即拦截并回灌原因 |
| 控制工具 | `tools/control_tools.py` | submit_result / request_block：执行者显式收口或申报阻塞 |
| 脱敏 | `safety/redact.py` | 私钥/API Key/密码等 6 类正则替换，输出回灌与工件导出前生效 |

**编排**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 多轮闭环 | `agent/orchestrator.py` 的 `run()` | 执行→Checklist 验收→missing 精确回流→重规划，`max_rounds` 默认 3 |
| 任务状态机 | `orchestrator/tasks.py` | 五状态 + 迁移表硬约束，非法迁移抛 `IllegalTransitionError` |
| 验收清单 | `orchestrator/checklist.py` | Completion Checklist：逐项 satisfied+evidence，空清单不算完成 |
| 验收双门 | `validator.py` | `completed = LLM 判定 AND 清单全满足`——模型口头说完成不够 |
| Retry Archive | `orchestrator/retry_archive.py` | 失败轨迹压缩为「原因+教训」，重试时注入上下文 |
| 编排快照 | `orchestrator/snapshot.py` | 复用 CheckpointStore，键 `<orch_id>-orchestration`，轻量（不含子任务轨迹） |
| 共享交付工作区 | `.orch_<id>/ws` | 同一编排内子任务共享产物目录（dep-chain 依赖此语义）；跨编排隔离 |
| 预算熔断 | `orchestrator.max_total_tokens`（默认 800000） | 超限把剩余 PENDING 整体转 BLOCKED |

**评测与工件**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 七层评测 | `eval/runner.py` + `layer7_multiagent.py` | Layer 1-6b 离线与真实对照 + Layer 7 多智能体基准 |
| 冻结基准 | `benchmarks/tasks.generated.json`（seed=20260819） | 参数化生成后落盘入库，可审查可 diff 可复现 |
| 三臂对照 | `eval/raw_baseline.py` | single_shot / naive_loop / harness 同任务集对比 |
| 机制消融 | `--ablate guard,retry,budget,validator` | 把某机制放宽到永不触发跑对照，量化其贡献 |
| 客观检查器 | `layer7_multiagent.py` 各 `check_*` | 真实 subprocess 执行产物并断言，不采信 Agent 自述 |
| 三类工件 | `artifacts.py` | trajectory.jsonl / checkpoint.json / metrics.json + report.md |
| trace.json | `observability/tracing.py` | OTLP 风格 span 树，事件驱动零侵入重建 |

**接口**

| 术语 | 对应代码 / 配置 | 在本项目中的含义 |
| --- | --- | --- |
| 事件总线 | `on_event` 回调 | harness/编排每步发语义事件；Tracer、SSE、评测器都是它的消费者 |
| 事件哨兵 | `{"type": "__done__"}` | SSE 队列收尾标记，前端收到具名 `done` 事件后关流 |
| 双 API 实现 | `serve --impl stdlib\|fastapi` | stdlib 零依赖同步；fastapi 提供 SSE 与异步提交 |
| 监控页 | `api/monitor_page.py` | 内嵌 HTML + vendored Vue 3，零构建离线可用 |
***

# 第一部分：项目背景与目标（先理解「为什么」）

## 1.1 它解决什么问题

大模型 API 的一次 `chat/completions` 调用能写一段代码，但**跑不成一个任务**：上下文会膨胀、文件会反复读、中断就丢状态、跑完说不清发生了什么。AgentMuster 把这四件事（外加三条）当作**工程问题**来解决，每个故障都有明确的机制与落点：

| 长链路任务的典型故障 | AgentMuster 的做法 | 实现位置 |
| --- | --- | --- |
| 上下文膨胀，长任务中途爆窗 | 软预算触发折叠 + 硬限额强制截断，三级裁剪策略链式降级 | `agentmuster/context/` |
| 同一文件反复读，token 白烧 | 任务/文件/关联三层结构化记忆 + SHA256 哈希去重，follow-up 自动注入父任务摘要 | `agentmuster/memory/` |
| 中断即重来，进度全丢 | Checkpoint/Resume + 工作区 SHA256 指纹漂移识别 | `agentmuster/checkpoint/` |
| 工具乱跑、路径逃逸、密钥进日志 | 白名单→Schema→沙箱→shell 名单→去重→振荡 Guard→HITL→脱敏的纵深安全链 | `agentmuster/safety/` |
| 模型空转/死循环/协议不兼容 | 空终答温和重问、重复振荡三重检测、NATIVE→TEXT_JSON 协议降级、截断自愈 | `agent/harness.py`、`models/local_openai.py` |
| 复杂目标单 Agent 一把梭容易失控 | Planner-Executor-Validator 多轮闭环：Checklist 客观验收、缺失项精确回流重规划、失败即时重试并注入教训、全局预算熔断 | `agent/orchestrator.py`、`orchestrator/` |
| 分不清「系统不行」还是「模型不行」 | 三臂裸基线对照（single_shot/naive_loop/harness）+ 七层评测 + 机制消融 | `agentmuster/eval/` |

一句定位：**AgentMuster 是一个面向代码仓库长链路任务的本地 Agent 运行底座**——核心运行时只依赖 PyYAML，全部测试与 Layer 1-5 评测离线可跑，模型侧通过 OpenAI 兼容端点接本地 Ollama/vLLM/llama.cpp，不依赖任何云端服务。

## 1.2 演进史：两个项目如何合并成一个

理解这个项目必须理解它的「血统」，这也是面试里最好讲的工程叙事：

**阶段一 · MyCoder（单 Agent 底座）**。先有一个单 Agent 运行底座：主循环、上下文治理、结构化记忆、Checkpoint、安全链、工件系统、七层评测的前五层。它的编排层 `agent/orchestrator.py` 是个**空壳**——`_default_planner` 永远把目标当成单子任务（源码就一行：`return [{"id": "sub-1", "goal": goal}]`），「分解→并行→聚合」一次跑完，没有验收、没有重试闭环。

**阶段二 · miniMaster（多智能体角色闭环）**。另一个项目验证了一套角色机制：Planner 拆解任务、Executor 瘦循环执行、Validator 按 Completion Checklist 验收，配上任务状态机、动作白名单、重复/振荡 Guard、失败轨迹归档重试（Retry Archive）、编排快照续跑，以及一套 8 任务真实基准 + 机制消融评测。它的短板是单 Agent 底座薄：上下文治理、结构化记忆、断点恢复、工件系统都不如 MyCoder 完整。

**阶段三 · 合并（AgentMuster）**。两个同源项目约 70% 重叠，合并方案经三轮评审定稿（`docs/MERGE_DESIGN.md`，11 项决策 D1-D11），分 5 批合入，每批全量测试绿 + CHANGELOG 条目：

| 批次 | 内容 | 测试增量 |
| --- | --- | --- |
| 批次① | 包名 `mycoder`→`agentmuster`（机械重命名独立成提交）+ 角色层八件套移植、Orchestrator 升级多轮闭环、编排快照续跑 | 272 → 308 |
| 批次② | 安全增强：控制工具（submit_result/request_block）、动作白名单 `safety/policy.py`、重复/振荡 Guard `safety/repeat_guard.py` 并入安全链、`RunResult` 新增 `blocked` 状态 | 308 → 327 |
| 批次③ | 协议自适应（NATIVE→TEXT_JSON 单向降级）+ 截断自愈 + MCP stdio 客户端 + 上下文配对不变量回归 + 死代码清理 | 327 → 341 |
| 批次④ | Layer 7 多智能体端到端基准（8 任务 + 客观检查器 + 机制消融开关）+ 编排工作区语义修正（隔离→共享交付工作区） | 341 → 348 |
| 批次⑤ | CI 恢复：双 OS 矩阵（ubuntu/windows × 3.11/3.12）+ ruff + mypy + pytest + 覆盖率门禁（全局 ≥75%、编排层 ≥90%） | — |
| 补记 | Layer 7 首次真实 Ollama 实测驱动 4 处修复（超时重试穿透/验收降级/max_tokens 限幅/指标落地） | 348 → 349 |

**关键决策点精选**（完整见 MERGE_DESIGN §1，面试可讲的取舍逻辑）：

- **D1 子任务执行架构 = 单循环改造**：角色机制**注入**现有 `AgentHarness`，不引入第二套主循环。两套主循环意味着两套安全链、两套可观测性、双倍维护面。
- **D9 LiveContextTrimmer 不移植组件、只移植不变量**：那个组件做按条消息裁剪，与本项目「按轮折叠」冲突；但它的 `tool_calls` 配对边界用例改写成了 `test_context_pairing.py` 回归测试——**不要它的实现，要它的教训**。
- **执行期修订 · 共享交付工作区**：批次①按「每子任务完全隔离」实现后，批次④发现会拆散 dep-chain 类复合目标（后任务需要用先任务的产出），改为**同一编排内共享交付工作区** `.orch_<id>/ws`，跨编排仍隔离——「机制服从任务语义」的典型案例。
- **零依赖不妥协**：原计划为协议层引入 `openai` SDK（extra `[llm]`），批次③改为纯 urllib 实现，核心零依赖叙事反而变强。

## 1.3 三层结构

合并后项目呈清晰的三层：

1. **单 Agent 底座**（`agentmuster/agent/harness.py` 及其依赖包）：上下文治理 / 结构化记忆 / Checkpoint / 纵深安全链 / 工件系统 / 可观测性——保证**一个** Agent 跑得稳、看得见、可恢复。
2. **多智能体编排**（`agentmuster/agent/orchestrator.py` + `agentmuster/orchestrator/`）：任务状态机 + Planner-Executor-Validator 多轮闭环 + Retry Archive + 编排级断点续跑——保证**一群** Agent 朝一个目标收敛且可验收。
3. **七层评测**（`agentmuster/eval/`）：Layer 1-5 离线（Mock 回放，度量系统能力）→ Layer 6/6b 真实模型与三臂对照 → Layer 7 多智能体基准与机制消融——保证每个机制都有**对照数字**背书。

## 1.4 非目标与边界（同样重要）

- **不引入 LangChain / LangGraph 等编排框架**——手写编排是两个前身项目的共同路线；核心只依赖 PyYAML，把「Agent 到底需要什么」这个问题亲自回答一遍（这也是本项目的学习价值所在）。
- **不追求 miniMaster 逐行保真**——语义保真优先，接口向本项目惯例对齐（如 `chat_structured` 改写为后端无关的 `structured_complete`）。
- **不在评测里冒称满分**——Layer 6 的 LLM 评委用 2b 小模型实测 0/4 不可靠，结果如实保留在报告里而非修改口径。
- **全端口绑 127.0.0.1**——本地工具，不是 SaaS。

***

# 第二部分：架构设计思路

## 2.1 五条设计哲学（贯穿全程，每条都有落地处）

1. **核心零依赖**。核心运行时只依赖 PyYAML；Web API、向量检索、OTel 桥接、MCP、真实模型全部是可选依赖组或零依赖降级实现。为什么：任意新机器 `pip install -e .` 之后测试与评测必须全离线可跑——这也是 CI 只装 requirements 文件就能过门禁的前提。落地：`pyproject.toml` 的 extras 分组（api/vector/otel/dev）、fastapi 缺失时 `serve --impl fastapi` 给出安装提示而非崩溃、OTel 缺失时 Tracer 静默降级。
2. **确定性优先**。可复现优先于「聪明」：默认 MockBackend 脚本回放；token 估算用「中文每字 1 token + 其余 4 字符/token」的启发式而非真实分词器；摘要默认 deterministic 纯字符串拼接；`ContextManager.assemble()` 每次从完整历史深拷贝重算，绝不增量折叠。为什么：评测、回归测试、三臂对照全部建立在「同输入同输出」之上。
3. **可观测是一等公民**。三类工件（轨迹/断点/指标报告）+ 零侵入事件总线：主循环只管 `_emit` 语义事件，Tracer/SSE/评测器都是 `on_event` 的消费者，埋点异常被 `contextlib.suppress` 吞掉——**埋点绝不拖垮主链路**。
4. **纵深防御**。模型输出永远不可信：从动作白名单到参数校验到沙箱到去重到振荡检测到 HITL 再到输出脱敏，安全不是一道门而是一条链，且**拦截原因会回灌给模型**促其纠偏，而不是静默失败。
5. **如实度量**。指标不凑满分：系统能力（Mock 回放）与模型能力（真实端点）口径分离；LLM 评委不可靠就写进报告；Layer 7 fizzbuzz 失败判定为小模型能力边界而非管道缺陷。面试时这条最能体现工程成熟度。

## 2.2 分层架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│              Orchestrator(多智能体多轮闭环,可选增强)               │
│   Planner ─→ 工作队列(就绪任务并行,共享交付工作区) ─→ Validator    │
│        ↑  Completion Checklist 验收 / missing 回流重规划 /        │
│        └── Retry Archive 教训注入 / 预算熔断 / 编排级 resume       │
│                        每子任务 = 一个独立 AgentHarness            │
├─────────────────────────────────────────────────────────────────┤
│                      AgentHarness (主循环)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Model   │  │  Tools   │  │ Context  │  │  Memory  │         │
│  │ Backend  │  │ Registry │  │ Manager  │  │  Store   │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       └──────────────┴──────────────┴──────────────┘            │
│  ┌──────────────────────────────────────────────────┐           │
│  │                   SafetyGuard                     │           │
│  │  白名单/参数校验/沙箱/shell名单/去重/振荡Guard/HITL/脱敏 │       │
│  └──────────────────────────────────────────────────┘           │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ CheckpointStore  │  │ ArtifactManager  │                     │
│  └──────────────────┘  └──────────────────┘                     │
│  ┌────────────── 横切层(对 Harness 零侵入) ──────────────┐        │
│  │ Observability(Tracer/trace.json + on_event 事件总线)   │       │
│  │ API(fastapi_server + event_bus 的 SSE 事件流)          │       │
│  └───────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
        │                          │
   MockBackend(离线确定性)   LocalOpenAIBackend(Ollama/vLLM/llama.cpp)
```

读图的三个要点：

- **Harness 是唯一编排中枢**：CLI、API、Orchestrator 最终都落在「构建一个 AgentHarness 并调 `run()`」上；Harness 对编排层一无所知（单向依赖）。
- **安全链是工具执行的必经之路**：七类内置工具 + MCP 代理工具共用同一条链，MCP 远端 schema 也被本地参数校验拦截。
- **横切层零侵入**：可观测性与 API 通过 `on_event` 事件总线挂接，不进主循环的调用路径。

## 2.3 装配关系：谁创建谁

项目大量使用「工厂 + 依赖注入」，测试时递假的进去就能隔离。看 `AgentHarness.build` 的真实源码（`agent/harness.py:165-216`）：

```python
@classmethod
def build(cls, config: Config, backend: ModelBackend | None = None,
          workspace_root: str | None = None, memory_root: str | None = None,
          approver=None, on_event=None) -> AgentHarness:
    from ..models import create_backend
    backend = backend or create_backend(config)          # 后端缺省按配置选
    ws_root = workspace_root or config.get("workspace.root", ".")
    ws = Workspace(ws_root, config.get("workspace.allow_absolute", False))
    from ..tools import build_registry
    registry = build_registry()                          # 7 个内置工具
    # MCP 外部工具接入(批次③):按配置连接 stdio server,失败降级纯内置工具
    mcp_cmd = config.get("tools.mcp.server_cmd")
    if mcp_cmd:
        from ..tools.mcp_client import attach_mcp_tools
        attach_mcp_tools(registry, server_cmd=str(mcp_cmd), …, on_event=on_event)
    memory = StructuredMemory(memory_root or config.get("memory.root", …), …)
    redactor = Redactor(enabled=config.get("safety.redaction_enabled", True))
    guard = SafetyGuard(config, ws, approver=approver, redactor=redactor)
    cp = CheckpointStore(config.get("checkpoint.root", …),
                         enabled=config.get("checkpoint.enabled", True))
    am = ArtifactManager(config.get("artifacts.root", …), config, redactor=redactor)
    # 摘要器:llm 模式复用主后端压缩折叠历史(失败自动回退确定性)
    summarizer = None
    if config.get("context.summarizer") == "llm":
        from ..context.summarizer import LLMSummarizer
        summarizer = LLMSummarizer(backend=backend)
    # 可观测性:Tracer 作为默认 on_event 消费者(零依赖,导出 trace.json)
    tracer = None
    if config.get("observability.enabled", True):
        from ..observability import Tracer
        tracer = Tracer(artifacts_root=…, enabled=True)
    harness = cls(config, backend, ws, registry, memory, guard, cp, am, redactor, …)

    def _dispatch(event: dict) -> None:
        if tracer is not None:
            tracer.handle(event)          # Tracer 与调用方回调同时收到事件
        if on_event is not None:
            on_event(event)
    harness.on_event = _dispatch
    return harness
```

三个值得记住的装配细节：

- **事件扇出**：`_dispatch` 闭包让 Tracer 与调用方（如 SSE EventBus）**同时**收到事件——harness 不知道有几个消费者，只知道广播。
- **所有组件从 Config 读自己的参数**（点路径 `cfg.get("context.keep_last_turns", 6)`），因此评测/对照只需要克隆 Config 改一个键——这是「评测只动一个变量」能成立的结构基础。
- `Orchestrator._build_harness`（第 9 站精读）对每个子任务重复这套装配，只换根路径与白名单——同一个工厂，两种角色。

## 2.4 一次任务的宏观数据流（俯瞰）

**单任务**（第 5.1 节逐行展开）：

```
TaskInput(goal, files_hint, follow_up_of, extra)
  → AgentHarness.run()
      记忆注入(父任务摘要 + retry 教训) → context.set_task()
      loop[max_steps=30]:
          context.assemble()      # 组装 + 三级裁剪(软预算/硬限额)
          backend.complete()      # Mock 脚本 or 本地 OpenAI 兼容端点
          ├─ 无工具调用 → 终答分支(空终答温和重问一次) → break
          └─ 有工具调用 → SafetyGuard 检查链 → Tool.execute()
                            → 记忆自动沉淀 → 脱敏 → 回填上下文
          checkpoint(interval/prune) + trajectory 追加 + on_event
  → RunResult(status, final_answer, steps, metrics, drift, control)
  → 工件导出(.agentmuster/artifacts/<task_id>/)
```

**多轮编排**（第 5.5 节逐行展开）：

```
goal → Planner.plan() → tasks[] + Completion Checklist
  loop[round ≤ max_rounds=3]:
      就绪任务(PENDING 且依赖满足)并行执行(每任务一个子 AgentHarness)
      失败 → Retry Archive 归档 → 轮内即时重入队(带教训)
      Validator.verify(goal, checklist, tasks) → apply_verdict
      ├─ verdict.completed AND checklist.is_complete → 通过, 落快照(True), break
      └─ 未过 → missing_requirements 精确回流 → Planner.replan(增量)
                预算熔断/死局检测可提前终止
  → aggregate() → orchestration.json(含 checklist/子任务/活动日志/交付工作区)
```

***

# 第三部分：技术栈与选型理由

| 技术 | 用在哪 | 为什么是它（而不是别的） |
| --- | --- | --- |
| **Python 3.11+** | 全项目 | 结构模式匹配、`StrEnum`、更快的解释器；3.10→3.11 是合并时主动抬的门槛 |
| **PyYAML（唯一核心依赖）** | 配置加载 | YAML 比 JSON 适合带注释的配置；为它放弃「绝对零依赖」是可接受的唯一妥协 |
| **urllib（标准库）** | `models/local_openai.py` HTTP 层 | 纯标准库实现 chat/completions 客户端 + SSE 流式解析 + 重试退避；对比 `openai` SDK：零依赖、协议细节（降级/截断自愈）完全可控、没有版本漂移风险 |
| **threading + ThreadPoolExecutor** | API 后台执行、编排并行 | 子任务 I/O 密集（等模型），线程模型足够；GIL 在此不是瓶颈，省去 asyncio 全栈复杂度 |
| **http.server（stdlib）** | `api/server.py` | 零依赖 HTTP 服务保证「裸 Python 也能起监控」；FastAPI 版本作为可选增强提供 SSE |
| **FastAPI + uvicorn（可选 `[api]`）** | `api/fastapi_server.py` | 异步 + SSE 是它的舒适区；`serve --impl` 双实现切换，默认 stdlib |
| **Vue 3（vendored 单文件）** | `static/vue.global.prod.js` | 监控页零构建、零 npm、离线可用——「vendor 一个 166KB 运行时」比「引入 Node 工具链」便宜得多 |
| **JSON Schema 子集（自研）** | `guard.validate_params` | 只需 required/类型/enum/min-max 五项检查；引 `jsonschema` 库换来的是依赖与报错不可控 |
| **HashingEmbedder + 纯 Python BM25** | `memory/vectors.py` | 零依赖语义检索基线（字符 n-gram MD5 哈希，确定性）；fastembed/bge-small 作为可选升级而非默认 |
| **pytest + pytest-cov + ruff + mypy** | 质量门 | 社区默认组合；覆盖率门禁不满足 pytest-cov 单阈值限制，故加 `scripts/check_coverage.py` 按路径断言（编排层 ≥90%） |
| **GitHub Actions（双 OS 矩阵）** | `.github/workflows/ci.yml` | ubuntu+windows × 3.11+3.12——Windows runner 暴露了 cp1252 编码、反斜杠穿越等四类真实缺陷（8.3 节是现成面试素材） |
| **QLoRA（bitsandbytes + TRL，支线）** | `kb_lora/` | RTX 4060 8GB 消费卡可跑的微调方案；与主项目完全解耦，自带 requirements |

**一个刻意回答的问题：为什么不用 LangChain/LangGraph？** 三个理由：(1) 学习目的——Harness 的核心难点（上下文预算、断点语义、安全链、评测口径）在框架里是被隐藏的，手写一遍才算掌握；(2) 工程目的——确定性可复现要求对每次模型调用、每次裁剪、每次落盘有完全控制权；(3) 叙事目的——面试时「我手写了 LangGraph 同类的编排层，并知道它在哪些点比框架做得更细/更粗」远比「我用过 LangGraph」有说服力。

***

# 第四部分：目录结构总览

## 4.1 完整目录树（注释版）

```
AgentMuster/
├── agentmuster/                    # 核心包
│   ├── cli.py                      # 8 个子命令入口(run/resume/serve/orchestrate/eval/benchmark/artifacts/doctor)
│   ├── config.py                   # DEFAULT 配置字典 + YAML 深合并 + 点路径 get/set
│   ├── state.py                    # 纯 dataclass 状态模型(Message/ToolCall/Step/TaskInput/RunResult)
│   ├── util.py                     # truncate/atomic_write/extract_json/parse_text_action/clean_subprocess_env
│   ├── artifacts.py                # 三类工件导出(trajectory.jsonl/checkpoint/metrics.json+report.md)
│   ├── tasks.py                    # 任务文件加载(.json / .md+frontmatter)
│   ├── cost.py                     # CostTracker 价目表核算(通配键 * 兜底)
│   ├── sft_collector.py            # 任务成功时采集 (instruction,output,context) SFT 样本
│   ├── models/                     # 模型后端
│   │   ├── base.py                 #   ModelBackend 抽象 + ModelResponse + state()/load_state() 断点钩子
│   │   ├── mock.py                 #   MockBackend:脚本回放,游标可恢复,确定性
│   │   └── local_openai.py         #   LocalOpenAIBackend:urllib+重试退避+SSE 流式+协议降级+截断自愈
│   ├── tools/                      # 工具框架
│   │   ├── base.py                 #   Tool 基类(name/description/parameters/danger) + ToolRegistry
│   │   ├── sandbox.py              #   Workspace 沙箱:resolve 五步链 + snapshot 指纹 + os.walk 剪枝
│   │   ├── file_tools.py           #   file_read/write/edit/list + grep_search
│   │   ├── shell_tool.py           #   shell_exec(白名单命令+黑名单模式,timeout 硬上限 30s)
│   │   ├── memory_tool.py          #   memory_query(查询结构化记忆)
│   │   ├── control_tools.py        #   submit_result/request_block(编排收口,不进默认注册表)
│   │   └── mcp_client.py           #   MCP stdio JSON-RPC 客户端 + MCPProxyTool 零转换注册
│   ├── safety/                     # 安全边界
│   │   ├── guard.py                #   SafetyGuard 检查链 + validate_params + ApprovalProvider 四实现
│   │   ├── policy.py               #   Role/Action/ActionPolicy 动作白名单
│   │   ├── repeat_guard.py         #   重复/振荡三重检测(连续/窗口/周期)
│   │   └── redact.py               #   6 类敏感信息正则脱敏
│   ├── context/                    # 上下文治理
│   │   ├── tokens.py               #   启发式 token 估算(CJK 1字/其余4字符)
│   │   ├── summarizer.py           #   Deterministic/LLM/Noop 三摘要器(LLM 失败回退确定性)
│   │   └── manager.py              #   ContextManager:组装 + 三级裁剪链,深拷贝不污染 raw_turns
│   ├── memory/                     # 结构化记忆
│   │   ├── store.py                #   StructuredMemory:任务/文件/关联三层,SHA256 去重,followup 注入
│   │   └── vectors.py              #   HashingEmbedder/VectorIndex/BM25/HybridRetriever
│   ├── checkpoint/                 # 断点
│   │   ├── store.py                #   CheckpointStore:atomic_write(Windows 重试),快照自包含
│   │   └── drift.py                #   WorkspaceDriftDetector:modified/added/deleted 三集合并运算
│   ├── agent/                      # 循环层
│   │   ├── harness.py              #   AgentHarness:主循环 + 工具执行链 + checkpoint 时机 + 事件发射
│   │   ├── orchestrator.py         #   Orchestrator:多轮闭环 + 并行调度 + 失败收口 + 快照续跑
│   │   └── prompts.py              #   Planner/Validator 身份层+协议层模板 + 失败压缩 prompt
│   ├── orchestrator/               # 编排八件套(批次①自 miniMaster 移植)
│   │   ├── tasks.py                #   Task/TaskStatus/ALLOWED_TRANSITIONS 状态机
│   │   ├── checklist.py            #   CompletionChecklist:apply_verdict/unmet/is_complete
│   │   ├── structured.py           #   structured_complete:JSON 提取 + 解析失败反馈重试环(≤3 次)
│   │   ├── planner.py              #   PlannerRole:plan/replan(增量,空任务语义重问)
│   │   ├── validator.py            #   ValidatorRole:verify + 代码级双门
│   │   ├── working_memory.py       #   角色视图渲染 + 有界活动日志(deque maxlen=50,线程安全)
│   │   ├── retry_archive.py        #   RetryArchive:按任务分桶归档教训
│   │   └── snapshot.py             #   编排快照(复用 CheckpointStore,键加 -orchestration 后缀)
│   ├── observability/
│   │   └── tracing.py              #   Span/Tracer:事件驱动重建 span 树,OTLP 风格导出,OTel 桥接
│   ├── api/
│   │   ├── server.py               #   stdlib 实现(零依赖,同步阻塞,遗留端点)
│   │   ├── fastapi_server.py       #   FastAPI 实现(异步提交+SSE+/api/compare 双跑)
│   │   ├── event_bus.py            #   TaskEventBus:按 task_id 路由的队列桥 + done 哨兵
│   │   ├── monitor_page.py         #   内嵌 HTML+CSS+JS 的 Vue 3 监控页
│   │   └── static/vue.global.prod.js  # vendored Vue 运行时(166KB,离线)
│   └── eval/                       # 七层评测
│       ├── runner.py               #   Layer 1-5:回归/上下文/记忆/恢复/检索
│       ├── benchmark.py            #   load_benchmarks(手写+冻结合并)
│       ├── experiment.py           #   compare_metrics/format_delta 对照原语
│       ├── judge.py                #   LLMJudge:严格 JSON 契约,解析失败即判负
│       ├── real.py                 #   Layer 6:真实模型端到端(completed∧断言∧judge 三者与)
│       ├── raw_baseline.py         #   Layer 6b:single_shot/naive_loop/harness 三臂
│       └── layer7_multiagent.py    #   Layer 7:8 任务+客观检查器+--ablate 消融
├── benchmarks/                     # 评测数据契约
│   ├── tasks.json                  #   26 手写任务(正例/负例/边界)
│   ├── tasks.generated.json        #   42 冻结任务(seed=20260819 生成后入库)
│   ├── retrieval.json(+extra)      #   82 条检索查询(exact/synonym/distractor/empty 四类)
│   ├── real_tasks.json             #   4 个真实编码任务(Layer 6/6b 共用)
│   └── generators.py               #   冻结生成器(--seed 参数化)
├── tests/                          # 349 项 pytest(24 文件);tests/orchestrator/ 六文件覆盖编排
├── examples/                       # demo.py(综合)/context_demo.py(上下文)/real_model_demo.py(Layer 6)
├── config/                         # default.yaml(本地) / docker.yaml(容器)
├── scripts/check_coverage.py       # 双阈值覆盖率门禁(全局≥75%,编排层≥90%)
├── kb_lora/                        # 企业知识库 LoRA 微调线(造数据→清洗导出→QLoRA 训练)
├── docs/                           # ARCHITECTURE/MERGE_DESIGN/TESTING/EVAL_HARDENING 等
├── .github/workflows/ci.yml        # 双 OS × 双 Python 矩阵 + ruff/mypy/pytest/覆盖率门禁
├── pyproject.toml                  # 打包 + extras(http/test/dev/api/vector/otel) + 工具配置
├── environment.yml / requirements*.txt / Dockerfile / docker-compose.yml / CHANGELOG.md
```

## 4.2 模块依赖关系（谁依赖谁）

```
cli.py ──→ config.py ──→ (DEFAULT)
  │
  ├──→ agent/harness.py ──→ models/(base→mock|local_openai)
  │         │        ├──→ tools/(sandbox, file_tools, shell_tool, memory_tool, mcp_client)
  │         │        ├──→ safety/(guard→policy, repeat_guard, redact)
  │         │        ├──→ context/(manager→tokens, summarizer)
  │         │        ├──→ memory/(store→vectors)
  │         │        ├──→ checkpoint/(store, drift)
  │         │        ├──→ artifacts.py / cost.py / sft_collector.py / state.py / util.py
  │         │        └──→ observability/tracing.py(经 on_event 挂接)
  │
  └──→ agent/orchestrator.py ──→ orchestrator/(tasks, checklist, structured,
                                  planner, validator, working_memory,
                                  retry_archive, snapshot)
              │                        （planner/validator → structured_complete → backend）
              └──→ 每个子任务 new 一个 agent/harness.py 的 AgentHarness

api/fastapi_server.py ──→ agent/(经 create_backend/harness.build) + api/event_bus.py
eval/runner.py ──→ agent/harness.py(评测量只改 Config 开关,其余不变)
```

三条读图结论：

1. **依赖方向永远向下**：编排层依赖 harness，harness 依赖各能力包，能力包之间几乎不横互依赖（`prompts.py` 刻意保持叶子模块——模块 docstring 明写「不 import 包内其他模块，可被 agent 与 orchestrator 两个包安全引用」）。
2. **Config 是唯一的「胶水」**：所有组件从 Config 读自己的参数，因此评测/对照只需要克隆 Config 改一个键。
3. **events 是唯一向上的通道**：子组件不持有父级引用，靠 `on_event` 回调上报——这是横切层零侵入的结构保证。

## 4.3 阅读顺序建议（第一次通读源码）

按依赖从底向上、先机制后循环：`state.py`/`config.py`/`util.py`（1 天）→ `context/` 与 `memory/`（1 天）→ `tools/` 与 `safety/`（1~2 天）→ `models/`（半天）→ `agent/harness.py` 精读（1 天）→ `orchestrator/` 八件套 + `agent/orchestrator.py` 精读（2 天）→ `eval/`（1 天）→ `api/` 与 `observability/`（半天）。
***

# 第五部分：核心流程（时序级拆解，逐行对照源码）

> 本部分把六条最关键的链路逐拍讲透，**每一条都贴出真实源码并逐段解读**。读懂本部分，第六部分的源码走读就只是「给已经理解的东西找到落点」。这部分也是面试的核心弹药库。

## 5.1 一次 run 的完整生命周期

入口：`python -m agentmuster run --task-file demo_task.json --workspace ./workspace`。假设任务为「创建 hello.py 并总结」。

### 第 0 拍 · 装配

`cli.py` 加载配置（显式传 `--config` 用 YAML 文件，否则用内置 DEFAULT）；任务文件若有 `script` 字段则强制 MockBackend；预置 `setup_files` 写入工作区；`AgentHarness.build()` 装配（源码见 2.3 节）。

### 第 1 拍 · 记忆注入（`agent/harness.py:280-297`）

两路内容合并为 memory_block，随后 `set_task` 落定并写启动断点：

```python
# agent/harness.py L280-297
        # follow-up 记忆注入:让后续任务直接拿到父任务的摘要,避免重读文件
        mem_block = ""
        if task.follow_up_of and self.memory is not None and \
                self.config.get("memory.followup_inject_summaries", True):
            mem_block = self.memory.followup_context(task_id=task.task_id,
                                                     parent_task_id=task.follow_up_of)
        # 编排层注入:子任务的 Retry Archive 教训(经 TaskInput.extra 传入)进入上下文,
        # 让重试任务直接拿到历史失败教训,避免重蹈覆辙
        retry_lessons = str((task.extra or {}).get("retry_lessons") or "")
        if retry_lessons:
            mem_block = f"{mem_block}\n{retry_lessons}".strip() if mem_block else retry_lessons
        self.context.set_task(task.goal, task.files_hint, mem_block)
        self._checkpoint(task, start_step, reason=reason)

        recorder.record({"type": "task_start", "task_id": task.task_id, "ts": now_iso(),
                         "follow_up_of": task.follow_up_of, "reason": reason})
        self._emit({"type": "task_start", "task_id": task.task_id, "ts": now_iso(),
                    "follow_up_of": task.follow_up_of, "reason": reason})
```

逐段解读：(1) follow-up 任务经 `followup_context()` 拿到父任务摘要 + 关联文件摘要（第 6 站精读该函数）；(2) 编排层重试时经 `TaskInput.extra["retry_lessons"]` 下发教训，这是**编排层与主循环之间唯一的知识通道**——harness 对编排一无所知，只认 `extra` 字段；(3) 启动即 checkpoint（reason=run/resume），保证「刚启动就崩」也能恢复；(4) `recorder.record`（写 trajectory.jsonl）与 `self._emit`（事件总线）**成对出现**——落盘与广播并行。

### 第 2 拍 · 主循环（`agent/harness.py:306-419`，全书最核心的 110 行）

```python
        try:
            for step_idx in range(start_step, max_steps):
                if stop_after_steps is not None and step_idx - start_step >= stop_after_steps:
                    status = "interrupted"
                    self._checkpoint(task, step_idx, reason="interrupt")
                    recorder.record({"type": "interrupt", "step": step_idx, "ts": now_iso()})
                    break

                # 1) 组装 + 裁剪上下文
                messages = self.context.assemble()
                self._emit({"type": "step_start", "index": step_idx, "ts": now_iso()})
                # 2) 调用模型
                t0 = time.time()
                resp = self.backend.complete(messages, self.registry.schemas())
                latency_ms = int((time.time() - t0) * 1000)

                # 2b) 计量:真实 usage(若后端提供)+ 延迟;后端未提供时 completion 用 0 占位
                usage = getattr(resp, "usage", None) or {}
                p_tokens = int(usage.get("prompt_tokens") or self.context.last_prune.after_tokens)
                c_tokens = int(usage.get("completion_tokens") or 0)
                model_name = getattr(self.backend, "model", "") or "unknown"
                step_cost = self.cost_tracker.cost_of(model_name, p_tokens, c_tokens)
                self._emit({"type": "model_call", "index": step_idx, "model": model_name,
                            "prompt_tokens": p_tokens, "completion_tokens": c_tokens,
                            "latency_ms": latency_ms, "ts": now_iso()})

                assistant = Message("assistant", resp.content,
                                    tool_calls=resp.tool_calls or None)

                # 3) 终答判断;空终答(无工具调用且无内容)不直接终止,先温和重问
                #    一次给模型补交机会(小模型典型失败模式),重问后仍空则如实终答
                if not resp.tool_calls:
                    nudge = (not (resp.content or "").strip()
                             and empty_nudges < max_empty_nudges)
                    if nudge:
                        empty_nudges += 1
                    final_answer = resp.content
                    self.context.append_turn(
                        assistant, [],
                        user=Message("user", _EMPTY_ANSWER_REMINDER) if nudge else None)
                    self._emit({"type": "step_end", "index": step_idx, "ts": now_iso()})
                    steps.append(Step(index=step_idx, assistant=assistant,
                                      prompt_tokens=p_tokens,
                                      prompt_before_tokens=self.context.last_prune.before_tokens,
                                      completion_tokens=c_tokens,
                                      pruned=self.context.last_prune.pruned,
                                      prune_strategies=self.context.last_prune.strategies,
                                      latency_ms=latency_ms))
                    …  # 指标累加 + trajectory 记录(同下文工具分支)
                    if nudge:
                        recorder.record({"type": "empty_answer_nudge", "step": step_idx,
                                         "ts": now_iso()})
                        continue                       # ← 重问后再给一轮机会
                    break                              # ← 真终答,退出主循环

                # 4) 执行工具
                calls, tool_msgs = self._execute_tools(resp.tool_calls, step_index=step_idx)
                self.context.append_turn(assistant, tool_msgs)

                step = Step(index=step_idx, assistant=assistant, tool_calls=calls, …)
                steps.append(step)
                self._record_step(recorder, step)
                self._emit({"type": "step_end", "index": step_idx, "ts": now_iso()})

                # 5) 指标 & checkpoint
                self.metrics.steps += 1
                self.metrics.prompt_tokens_total += p_tokens
                …
                if self.context.last_prune.pruned:
                    self.metrics.prunes += 1
                    self.metrics.compression_ratios.append(self.context.last_prune.ratio)
                    if self.config.get("checkpoint.on_prune", True):
                        self._checkpoint(task, step_idx + 1, reason="prune")
                interval = int(self.config.get("checkpoint.interval_steps", 4))
                if self.config.get("checkpoint.enabled", True) and \
                        (step_idx + 1 - start_step) % interval == 0:
                    self._checkpoint(task, step_idx + 1, reason="interval")
                if self._control_signal is not None:
                    # 控制动作收口(批次②):submit_result / request_block 终止主循环
                    signal = self._control_signal
                    if signal["action"] == SUBMIT_RESULT:
                        status = "completed"
                        final_answer = str(signal.get("summary", ""))
                        control = {"action": SUBMIT_RESULT,
                                   "success": bool(signal.get("success"))}
                    else:
                        status = "blocked"
                        final_answer = str(signal.get("reason", "未说明原因"))
                        control = {"action": REQUEST_BLOCK}
                    recorder.record({"type": "control_end", "action": signal["action"],
                                     "status": status, "ts": now_iso()})
                    self._emit({"type": "control_end", "action": signal["action"],
                                "status": status, "ts": now_iso()})
                    break
            else:
                status = "max_steps"                    # ← for-else:循环自然耗尽
                recorder.record({"type": "max_steps", "ts": now_iso()})
        except Exception as e:
            status = "error"
            error = f"{type(e).__name__}: {e}"
            self.logger.exception("任务 %s 异常", task.task_id)
            self._checkpoint(task, len(steps), reason="error")   # ← 异常也保留现场
            recorder.record({"type": "error", "error": error, "ts": now_iso()})
```

这段代码有 **7 个面试级细节**：

1. **`for-else` 语义**：Python 的 for-else 在循环**未被 break**（自然耗尽）时执行 else——精确对应「步数用尽而非主动收口」，所以 status=max_steps。
2. **双份 token 记账**：`Step` 同时记 `prompt_tokens`（裁剪后，真实送入）与 `prompt_before_tokens`（裁剪前）——Layer 2 评测算压缩率靠这对字段，`Step` 源码注释明写「评测压缩率用」。
3. **usage 三重兜底**：真实 usage 优先 → prompt 缺失用 `last_prune.after_tokens`（裁剪后 token 占位）→ completion 缺失用 0（后续启发式在第 2 站）。
4. **空终答温和重问**：`nudge` 条件 = 内容为空 **且** 未超 `empty_answer_nudges` 预算；重问的实现是往上下文追加一条 user 提醒（`_EMPTY_ANSWER_REMINDER`，见 `harness.py:86-89`：「你的上一条回复是空的。请继续完成当前任务：对文件的修改必须通过 file_edit / file_write 工具落盘，完成后再给出简洁的最终回答。」）然后 `continue`——注意轮结构多了可选 `user` 位（`append_turn(assistant, tool_msgs, user=...)`），checkpoint 序列化向后兼容。
5. **checkpoint 的两种额外时机**：本轮发生裁剪 → `reason="prune"` 立即落盘（裁剪是深拷贝重算，崩在半路也能回到裁剪前现场）；每 `interval_steps=4` 步 → `reason="interval"`，注意模数基于 `step_idx + 1 - start_step`（相对恢复起点计数，resume 后节奏不乱）。
6. **控制信号检查在循环尾部**：`_control_signal` 由 `_execute_tools` 里的控制工具分流写入（5.2 节），这里只消费——`submit_result` → completed + `control={"action","success"}`；`request_block` → **blocked**（批次②新增终态）。`control` 字段随 `RunResult` 上行，编排层据此决定 DONE/FAILED/BLOCKED。
7. **异常也落断点**：`except` 分支先 `status="error"` 再 `checkpoint(reason="error")`——错误现场可复盘是「可观测」哲学的延伸。

### 第 3 拍 · 收尾（`agent/harness.py:427-454`）

```python
        # 收尾:终局 checkpoint + 记忆任务摘要 + 导出工件
        if status not in ("interrupted", "error"):
            self._checkpoint(task, len(steps), reason="final")
        self._remember_task(task, status, final_answer)
        self._sync_guard_metrics()
        result_payload = {"status": status, "final_answer": final_answer, "error": error}

        # 可选 SFT 样本采集:任务成功结束时,把 (instruction=goal, output=final_answer)
        # 落成 sft_samples.jsonl,供后续 LoRA 微调使用。默认关闭,不破坏既有行为。
        if (status == "completed"
                and self.config.get("artifacts.sft_log", False)):
            write_sft_sample(
                task_dir=self.artifacts.task_dir(task.task_id),
                task_id=task.task_id,
                instruction=task.goal,
                output=final_answer,
                context=None,  # 企业知识库场景可在此注入检索到的 KB 上下文
                status=status,
                redactor=self.redactor,
            )

        self.artifacts.export(task.task_id, self.metrics, result_payload,
                              checkpoint_obj=self.checkpoint.load(task.task_id))
        recorder.record({"type": "task_end", "status": status, "ts": now_iso()})
        self._emit({"type": "task_end", "status": status, "ts": now_iso()})
        return RunResult(task_id=task.task_id, status=status, final_answer=final_answer,
                         steps=steps, metrics=self.metrics.snapshot(), drift=drift, error=error,
                         control=control)
```

收尾顺序有讲究：final checkpoint（interrupted/error 除外——它们已有现场断点）→ `_remember_task` 把任务摘要沉淀进结构化记忆（供 follow-up 复用）→ `_sync_guard_metrics` 把 guard 的 `read_cache_hits/skipped_repeats/denied` 同步进 metrics → 可选 SFT 采集（只采 completed，默认关）→ `artifacts.export` 导出三类工件（全量过 Redactor）→ 发 `task_end` → 返回 `RunResult`。

一次运行在 `.agentmuster/` 下沉淀：

```
.agentmuster/
├── artifacts/demo_hello/   # trajectory.jsonl(逐步轨迹) + metrics.json + report.md (+trace.json)
├── checkpoints/            # checkpoint.json(可 resume)
└── memory/                 # tasks.json / files.json / relations.json 三层记忆
```

### 5.1b · resume 的恢复流程（`agent/harness.py:234-267`）

```python
    def resume(self, task_id: str, stop_after_steps: int | None = None) -> RunResult:
        cp = self.checkpoint.load(task_id)
        if cp is None:
            return RunResult(task_id, status="error", error=f"找不到断点: {task_id}")
        # 1) 工作区漂移识别
        drift: DriftReport | None = None
        if self.config.get("checkpoint.detect_drift", True):
            before = cp.get("workspace_fingerprint", {})
            after = self.workspace.snapshot()
            drift = WorkspaceDriftDetector.compare(before, after)
            self.logger.info("恢复 %s: %s", task_id, drift.summary())
        # 2) 恢复上下文
        ctx = cp.get("context", {})
        self.backend.load_state(cp.get("backend_state", {}))     # Mock 剧本游标复位
        self.context.set_task(ctx.get("goal", ""), ctx.get("files_hint", []),
                              ctx.get("memory_block", ""))
        self.context.raw_turns = [_turn_from_dict(t) for t in ctx.get("raw_turns", [])]
        if ctx.get("last_prune"):
            self.context.last_prune = PruneInfo(…)
        task = TaskInput(task_id=cp["task_id"], goal=…, files_hint=…,
                         follow_up_of=…, extra=…)
        metrics = _metrics_restore(cp.get("metrics", {}))
        drift_dict = None if drift is None else {
            "modified": drift.modified, "added": drift.added, "deleted": drift.deleted,
            "is_drift": drift.is_drift, "summary": drift.summary(),
        }
        return self._run(task, start_step=cp.get("step_index", 0), metrics=metrics,
                         stop_after_steps=stop_after_steps, drift=drift_dict, reason="resume")
```

要点：恢复四件事——上下文（raw_turns 逐轮重建）、后端游标（`backend.load_state`）、指标（`_metrics_restore` 逐字段回填）、起始步（`start_step=step_index`，主循环从 `step_index` 继续）。漂移检测**先于**一切恢复动作：先确认「世界还是我以为的样子」，再续跑。
### 5.1c trajectory.jsonl 逐行解读（真实记录样例）

以 README 的 `demo_hello` 任务（两步 Mock 脚本：file_write → 终答）为例，运行后在 `.agentmuster/artifacts/demo_hello/trajectory.jsonl` 里逐行追加的记录长这样（**格式为真实记录结构，数值取自 README 实测运行**，长字符串略缩）：

```json
{"type": "task_start", "task_id": "demo_hello", "ts": "2026-10-02T14:32:01.114",
 "follow_up_of": null, "reason": "run"}

{"type": "step", "index": 0,
 "assistant": {"role": "assistant", "content": "",
   "tool_calls": [{"id": "call_0", "name": "file_write",
                   "arguments": {"path": "hello.py",
                                 "content": "def greet():\n    return 'hello'\n"}}]},
 "tool_calls": [{"id": "call_0", "name": "file_write",
                 "arguments": {"path": "hello.py", "content": "…"},
                 "status": "ok", "error": null,
                 "meta": {"path": "hello.py", "file_hash": "9f2ac3…", "size": 30}}],
 "prompt_tokens": 279, "prompt_before_tokens": 279,
 "completion_tokens": 10, "pruned": false, "prune_strategies": [],
 "latency_ms": 4, "ts": "2026-10-02T14:32:01.121"}

{"type": "step", "index": 1,
 "assistant": {"role": "assistant", "content": "已创建 hello.py,任务完成。", "tool_calls": null},
 "tool_calls": [],
 "prompt_tokens": 331, "prompt_before_tokens": 331,
 "completion_tokens": 20, "pruned": false, "prune_strategies": [],
 "latency_ms": 3, "ts": "2026-10-02T14:32:01.125"}

{"type": "task_end", "status": "completed", "ts": "2026-10-02T14:32:01.126"}
```

逐字段解读（这是复盘任何一次运行的钥匙）：

- **`assistant` vs `tool_calls`**：前者是模型本轮的原始响应（content + 发起的调用），后者是**执行后的调用记录**——`status`（ok/denied/error/skipped）与 `meta`（file_hash/cache_hit/danger 等）是执行侧补上的。对比这两块，一眼看出「模型想干什么」与「实际发生了什么」。
- **`prompt_tokens` 与 `prompt_before_tokens`**：本例无裁剪所以相等；长任务里 before > after，差值就是治理省下的 token（Layer 2 评压缩率的原始数据）。
- **`completion_tokens: 10`**：Mock 约定——工具调用轮固定记 10，终答轮按内容估算（`mock.py:79` 与 `:85`）。真实后端则透传 API usage。
- **被拦截长什么样**：若模型调用被沙箱拒绝，对应 tool_calls 元素的 `status` 是 `"denied"`、`error` 是拦截原因原文（「路径逃逸被拦截(超出工作区)： …」）、`assistant.content` 里的回灌文本以 `[已拦截]` 开头——复盘安全行为不用翻日志。
- **`prune_strategies`**：一旦非空（如 `["fold_old_turns"]`），说明该步触发了裁剪；`checkpoint.on_prune=true` 时这一步之后紧跟一次 prune 断点。

注意 trajectory 与事件流的**分工**：`checkpoint`、`model_call`、`tool_call`、`control_end` 等只进事件总线（Tracer/SSE 消费），trajectory 只落 `task_start/step/task_end` 与四种过程记录（nudge/max_steps/error/interrupt）。两份记录视角不同、互为补充。
## 5.2 一次工具调用的安全链全流程

这是全项目防御最密的路径，也是面试最常被追问的路径。**核实后的真实顺序**：前置分流（控制工具）→ 0.动作白名单 → 1.参数校验 → 2.路径沙箱 → 3.shell 治理 → 4.去重缓存 → 4b.振荡 Guard → 5.HITL 标记 → 审批 → 执行 → 记忆沉淀 → 脱敏回灌。

### 5.2.1 前置分流：控制工具不走安全链（`agent/harness.py:465-487`）

```python
        for tc in raw_calls[:max_calls]:                  # 每轮最多 8 个调用
            name = tc.get("name", "")
            raw_args = tc.get("arguments", "{}")
            # 解析 arguments：支持 JSON 字符串或字典格式
            if isinstance(raw_args, str):
                try:
                    params = json.loads(raw_args)
                except json.JSONDecodeError:
                    params = {}                           # 坏 JSON 按 {} 处理,不崩
            elif isinstance(raw_args, dict):
                params = raw_args
            else:
                params = {}
            # 控制动作(批次②):不走安全链/注册表,直接作为本轮终态信号
            if name in CONTROL_TOOLS:
                call = ToolCall(id=tc.get("id", short_id("call_")), name=name,
                                arguments=params, status="ok", meta={"control": name})
                calls.append(call)
                tool_msgs.append(Message("tool", f"[控制动作] {name} 已受理", name=name,
                                         tool_call_id=tc.get("id", "")))
                self._control_signal = {"action": name, **params}
                break
```

`CONTROL_TOOLS = frozenset({SUBMIT_RESULT, REQUEST_BLOCK})`（`tools/control_tools.py:17`）。为什么要前置分流：控制动作是**元层语义**（任务该结束了/该申报阻塞了），不是业务操作——让它过安全链既无意义又可能被白名单误伤。注意 `break`：控制动作出现即终止本轮工具循环（同轮后续调用不再执行）。

### 5.2.2 SafetyGuard.check 的九检查点（`safety/guard.py:148-211`，完整源码）

```python
    def check(self, tool: Tool, params: dict,
              allowed_tools: set[str] | None = None) -> GuardResult:
        # 0. 动作白名单(Action Policy,批次②):越权即拦截,拒绝原因回灌给模型
        if allowed_tools is not None and tool.name not in allowed_tools:
            self.denied += 1
            return GuardResult(False, reason=(
                f"角色越权: 动作 '{tool.name}' 不在白名单 {sorted(allowed_tools)} 内,"
                "操作已被拦截。请改用白名单内的工具,或用 submit_result / request_block 收口。"))

        # 1. 参数校验
        errors = validate_params(tool.parameters, params)
        if errors:
            self.denied += 1
            return GuardResult(False, reason="参数校验失败: " + "; ".join(errors))

        # 2. 路径隔离(含 shell.cwd)
        if tool.name in self._PATH_TOOLS:
            for key in ("path", "cwd"):
                if params.get(key):
                    try:
                        self.workspace.resolve(params[key])
                    except PathEscapeError as e:
                        self.denied += 1
                        return GuardResult(False, reason=str(e))

        # 3. shell 白名单/黑名单
        if tool.name == "shell_exec":
            reason = self._check_shell(params.get("command", ""))
            if reason:
                self.denied += 1
                return GuardResult(False, reason=reason)

        # 4. 重复调用拦截
        if self.config.get("safety.dedup_enabled", True):
            key = self._dedup_key(tool.name, params)
            if key in self._dedup:
                count, last_output = self._dedup[key]
                if tool.danger == HITL or tool.name in ("file_write", "file_edit"):
                    self.skipped_repeats += 1
                else:
                    self.read_cache_hits += 1
                # 更新计数,返回缓存输出(短路由,不再执行)
                self._dedup[key] = (count + 1, last_output)
                # 缓存命中也计入 Guard 指纹:反复重读同一内容同样是刷步行为
                if self.repeat_guard is not None and self._count_cache_hits:
                    verdict = self.repeat_guard.check(tool.name, params)
                    if not verdict.allowed:
                        self.denied += 1
                        return GuardResult(False, reason=verdict.message or "Guard 拦截")
                return GuardResult(True, cached_output=last_output,
                                   reason="重复调用被拦截,复用缓存结果", danger=tool.danger,
                                   action={"tool": tool.name, "params": params, "repeat": count + 1})

        # 4b. 重复/振荡动作 Guard(批次②:连续重复/窗口计数/周期振荡三重检测)
        if self.repeat_guard is not None:
            verdict = self.repeat_guard.check(tool.name, params)
            if not verdict.allowed:
                self.denied += 1
                return GuardResult(False, reason=verdict.message or "Guard 拦截")

        # 5. HITL 审批
        needs = tool.danger == HITL
        action = {"tool": tool.name, "params": params, "danger": tool.danger}
        return GuardResult(True, needs_approval=needs, reason="", danger=tool.danger, action=action)
```

逐段解读：

- **第 0 步白名单**：`allowed_tools` 非 None 才生效（单 Agent 场景传 None = 不限，保持既有行为）；拒绝文案里**带白名单全量与改道建议**——这是「拦截原因回灌」设计：模型看到这段文本就知道下一步该怎么办。
- **第 1 步参数校验**：`validate_params` 是自研 JSON Schema 子集（`guard.py:29-51`），查五项：required 缺失、未知参数（比标准 JSON Schema 更严格，直接判错）、类型（`_TYPE_MAP`，`number` 接受 int/float）、enum、integer 的 minimum/maximum。
- **第 2 步路径隔离**：`_PATH_TOOLS = {file_read, file_write, file_edit, grep_search, shell_exec}`——5 个带路径参数的工具全部过 `Workspace.resolve`（五步链见第 3 站）。
- **第 3 步 shell 治理**（`guard.py:226-239`）：

```python
    def _check_shell(self, command: str) -> str | None:
        allow = set(self.config.get("safety.shell.allow_commands", []))
        deny = self.config.get("safety.shell.deny_patterns", [])
        tokens = command.strip().split()
        if not tokens:
            return "空命令"
        base = tokens[0].lower()
        if base not in {a.lower() for a in allow}:
            return f"命令不在白名单: {tokens[0]}(白名单={sorted(allow)})"
        for pat in deny:
            if re.search(pat, command):
                return f"命中高危模式 {pat!r},已拦截"
        return None
```

  双重逻辑：首 token（小写）必须在 `allow_commands`（echo/ls/cat/git/python 等 14 个）内；再对**整条命令字符串**逐条 `re.search` 黑名单（`rm\s+-rf`、`curl`、fork bomb `:(){` 等 10 个）。白名单防「跑不该跑的」，黑名单防「白名单命令拼出危险参数」（如 `git` 白名单内但接 `; rm -rf /`）。
- **第 4 步去重 + 4b Guard 的协作关系（最容易答错的点）**：去重命中时**先**把缓存命中喂给振荡 Guard（`_count_cache_hits=True` 默认开）——否则「反复重读同一文件」会被去重层放行永远到不了 Guard；Guard 没拦才短路由返回缓存。读类（`read_cache_hits`）与写类/HITL（`skipped_repeats`）只是指标口径不同，**行为相同**（都返回缓存、不再执行）。
- **第 5 步只标记不裁决**：`needs_approval=True` 交给 harness 去调 `guard.approve()`——审批 Provider（Prompt/AllowAll/DenyAll/Callback）是可注入策略，与检查链解耦。

### 5.2.3 harness 侧的审批与执行（`agent/harness.py:509-563`）

```python
    def _run_one_tool(self, tool, params: dict, ctx: ToolContext) -> tuple[str, dict]:
        """单次工具调用的安全链 + 执行。返回 (输出文本, meta)。"""
        meta: dict[str, Any] = {}
        gr = self.guard.check(tool, params, allowed_tools=self.allowed_tools)
        if not gr.allowed:
            meta.update(status="denied", error=gr.reason)
            return f"[已拦截] {gr.reason}", meta
        if gr.needs_approval:
            if not self.guard.approve(gr.action):
                meta.update(status="denied", error="人工审批未通过")
                return "[已拦截] 人工审批未通过(高风险操作)", meta
            meta["hitl_approved"] = True
        # 去重短路
        if gr.cached_output is not None:
            meta.update(status="ok", cache_hit=True, reason=gr.reason)
            return gr.cached_output, meta
        # 真正的执行
        try:
            result = tool.execute(ctx, **params)
            output = result.output if result.output else result.error
            meta.update(status="ok" if result.ok else "error",
                        error=(result.error or None), **result.meta)
            if result.ok:
                self.guard.record_executed(tool, params, output)
                self._after_tool(tool.name, result.meta)
        except Exception as e:
            meta.update(status="error", error=str(e))
            output = f"[工具异常] {type(e).__name__}: {e}"
        # 脱敏(输出进上下文前)
        return self.redactor.redact(output), meta
```

以及执行成功后的记忆自动沉淀（`agent/harness.py:540-563`）：

```python
    def _after_tool(self, name: str, tool_meta: dict) -> None:
        """工具执行成功后的善后:统计 + 文件摘要沉淀。"""
        self.metrics.tool_calls += 1
        if name == "file_write" or name == "file_edit":
            self.metrics.write_calls += 1
        elif name == "file_read":
            self.metrics.read_calls += 1
        elif name == "memory_query":
            self.metrics.memory_queries += 1
        # 记忆:自动沉淀文件摘要(读/写/改之后)
        if name in self._FILE_TOOLS and self.memory is not None and \
                self.config.get("memory.auto_remember_files", True):
            path = tool_meta.get("path")
            if path:
                try:
                    content = self.workspace.read_text(path) or ""
                    digest = tool_meta.get("file_hash")
                    updated, _ = self.memory.remember_file(
                        path=path, content=content, sha256=digest or "",
                        task_id=self.current_task_id)
                    if updated:
                        self.metrics.files_remembered += 1
                except Exception:
                    pass
```

**面试级细节**：(1) 一切拒绝都是 `[已拦截] 原因` 文本回灌——安全链同时是教学链，模型能自我纠偏；(2) 工具异常被捕获为文本**不中断主循环**——单个工具失败不应杀死整个任务；(3) `record_executed` 在执行**成功后**才登记去重缓存（失败的调用不缓存，重试合法）；(4) `meta` 里的 `file_hash` 由工具层算好带回，`_after_tool` 直接复用避免二次读盘算哈希；(5) 脱敏是**输出侧**处理，在回灌上下文前最后一刻执行；(6) 记忆沉淀对模型**透明**——模型不需要「记得去存记忆」这个动作，读写文件后自动发生。

### 5.2.4 审批 Provider 四实现（`safety/guard.py:64-94`）

```python
class ApprovalProvider:
    """HITL 审批接口;不同策略注入不同实现。"""
    def approve(self, action: dict) -> bool:
        raise NotImplementedError

class AllowAllProvider(ApprovalProvider):
    def approve(self, action: dict) -> bool:
        return True

class DenyAllProvider(ApprovalProvider):
    def approve(self, action: dict) -> bool:
        return False

class CallbackProvider(ApprovalProvider):
    """测试/脚本用:把审批决定委托给一个回调。"""
    def __init__(self, fn):
        self.fn = fn
    def approve(self, action: dict) -> bool:
        return bool(self.fn(action))

class PromptProvider(ApprovalProvider):
    """交互式审批:stdin 输入 y/n(本地 CLI 使用)。"""
    def approve(self, action: dict) -> bool:
        print("\n⚠ 需要人工审批的高风险操作:")
        print("  " + json.dumps(action, ensure_ascii=False, indent=2))
        ans = input("  是否允许?[y/N] ").strip().lower()
        return ans in ("y", "yes")
```

三档策略映射在 `_default_approver`（`guard.py:135-138`）：`safety.hitl_policy` 的 `allow/deny/prompt` 各对应一个 Provider，默认 `prompt`。注意：编排子任务用 `AllowAllProvider()`（无人值守），测试用 `CallbackProvider`——**策略与机制分离**的教科书案例。

## 5.3 上下文裁剪决策树（逐行对照 `context/manager.py`）

### 5.3.1 组装与三级裁剪（`context/manager.py:107-151`）

```python
    def assemble(self) -> list[Message]:
        """组装并裁剪,返回送入模型的消息列表;裁剪刀口记录在 last_prune。

        注意:裁剪在"深拷贝的消息"上进行,绝不改动 raw_turns 里的原始历史,
        保证同一历史可被多轮 assemble 重复、确定性地重放(打底评测可复现)。
        """
        cfg = self.config
        base = self._base_messages()
        all_turns = self._flatten(self.raw_turns)
        before = estimate_messages(base + all_turns)  # 不做治理的 prompt 长度

        keep = max(1, int(cfg.get("context.keep_last_turns", 6)))
        hard = int(cfg.get("context.hard_limit_tokens", 6000))
        strategies: list[str] = []

        visible = self.raw_turns[-keep:] if len(self.raw_turns) > keep else self.raw_turns
        folded = self.raw_turns[:-keep] if len(self.raw_turns) > keep else []
        if folded:
            strategies.append("fold_old_turns")

        msgs = list(base)
        if folded:
            msgs.append(Message("system", "# 历史摘要\n" + self._fold_summary(folded)))
        msgs.extend(copy.deepcopy(self._flatten(visible)))

        # 兜底策略 1:仍超硬限 -> 折叠到只保留最近 1 轮原文
        if estimate_messages(msgs) > hard and len(visible) > 1:
            strategies.append("drop_stale_turns")
            visible = self.raw_turns[-1:]
            folded = self.raw_turns[:-1]
            msgs = list(base)
            msgs.append(Message("system", "# 历史摘要\n" + self._fold_summary(folded)))
            msgs.extend(copy.deepcopy(self._flatten(visible)))

        # 兜底策略 2:硬限额强制收缩,逐级截断最长消息,保证 100% 预算内
        if estimate_messages(msgs) > hard:
            strategies.append("truncate_long_content")
            msgs = self._enforce_budget(msgs, hard)

        after = estimate_messages(msgs)
        self.last_prune = PruneInfo(
            before_tokens=before, after_tokens=after,
            pruned=after < before, strategies=strategies,
        )
        return msgs
```

base 消息的构成（`manager.py:77-86`）：`SYSTEM_PROMPT`（角色+纪律：用相对路径、优先用摘要避免重读、完成就给终答）→ `# 任务目标`（user）→ `# 当前处理文件`（system）→ 记忆块（system，follow-up 注入/Retry 教训都进这里）。

### 5.3.2 硬兜底算法（`context/manager.py:153-168`）

```python
    def _enforce_budget(self, msgs: list[Message], hard: int) -> list[Message]:
        """把 prompt 硬压到 hard 以内:先截断超长内容,再收缩最长消息。"""
        cap = int(self.config.get("context.max_file_content_chars", 8000))
        for m in msgs:
            if len(m.content) > cap:
                m.content = truncate(m.content, cap)
        # 确定性收缩:反复把最长的消息缩到 60%,直到达标或无法再缩
        while estimate_messages(msgs) > hard:
            candidates = [m for m in msgs if m.content]
            if not candidates:
                break
            largest = max(candidates, key=lambda m: len(m.content))
            if len(largest.content) <= 40:
                break
            largest.content = truncate(largest.content, max(40, int(len(largest.content) * 0.6)))
        return msgs
```

两级：先按 `max_file_content_chars=8000` 头尾截断超长消息（`util.truncate` 保 60% 头部 + 尾部 + 截断标记）；再循环把最长消息缩到 60%（下限 40 字符，保证循环可终止）直到达标。**理论上限内 100% 达标**——`test_context.py::test_hard_limit_enforced` 固化。

### 5.3.3 token 估算器（`context/tokens.py:14-37`）

```python
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))          # [\u4e00-\u9fff\u3400-\u4dbf]
    other = len(text) - cjk
    # 分段避免单个超长 ASCII 块被 4 整除后低估;+1 保证非空文本至少 1 token
    return cjk + (other + 3) // 4

def estimate_messages(messages: list) -> int:
    total = 0
    for m in messages:
        if isinstance(m, dict):
            …
        else:
            total += 4 + estimate_tokens(getattr(m, "content", "") or "")  # 角色/结构约 4 token
            if getattr(m, "tool_calls", None):
                total += estimate_tokens(str(m.tool_calls))
    return total
```

设计目标（模块 docstring 原话）：「估算只需具备**单调性与稳定性**，不需要与真实 tokenizer 分毫不差。」——一致性来自「永远用同一把尺子」，这让软预算/硬限额的比较、评测的压缩率统计全部自洽。

### 5.3.4 为什么「轮」是原子单位

`append_turn(assistant, tool_msgs, user=None)`（`manager.py:63-69`）把 assistant+tool 成组追加；`_flatten` 按轮展开。OpenAI 协议强要求每条 tool 消息的 `tool_call_id` 都能在**前方的 assistant 消息**里找到发起者——按轮折叠使这个配对**结构上不可能被裁剪拆散**。`tests/test_context_pairing.py` 把这条不变量固化成回归测试（源自被放弃的 LiveContextTrimmer 组件的教训，MERGE_DESIGN 决策 D9）：「80 token 紧预算下裁剪仍配对」与「无裁剪全保留」两个用例。

### 5.3.5 摘要器三档（`context/summarizer.py`）

```python
class DeterministicSummarizer(Summarizer):
    """确定性压缩:保留助手结论首句 + 每步工具名与结果首片段。"""

    def summarize_turn(self, step_index: int, assistant_content: str,
                       tool_results: list[tuple[str, str]]) -> str:
        parts = [f"[步骤 {step_index}]"]
        if assistant_content:
            parts.append("助手结论: " + self.summarize_text(assistant_content, 160))
        for name, out in tool_results:
            parts.append(f"- {name}: {self.summarize_text(out, 120)}")
        return "\n".join(parts)


class LLMSummarizer(Summarizer):
    def summarize_turn(self, step_index: int, assistant_content: str,
                       tool_results: list[tuple[str, str]]) -> str:
        if self.backend is None:
            return self.fallback.summarize_turn(step_index, assistant_content, tool_results)
        …
        try:
            resp = self.backend.complete(messages, tools=None, temperature=0.0)
            text = (resp.content or "").strip()
        except Exception:
            text = ""
        if not text:                                   # backend 为 None/抛异常/返回空
            return self.fallback.summarize_turn(step_index, assistant_content, tool_results)
        return truncate(text, self.max_chars)
```

三档：`deterministic`（默认，纯字符串拼接零随机性）/ `llm`（模型压缩，**三种失败全部回退确定性**——裁剪链永不中断）/ `noop`（只输出「[步骤 N 已折叠]」，评测对照用）。实测平均压缩率约 80%，预算内完成率 100%。
## 5.4 断点与漂移识别（逐行对照）

### 5.4.1 快照内容（`agent/harness.py:566-593`）

```python
    def _checkpoint(self, task: TaskInput, step: int, reason: str) -> None:
        if not self.config.get("checkpoint.enabled", True):
            return
        snap = {
            "version": 1,
            "task_id": task.task_id,
            "reason": reason,
            "step_index": step,
            "backend_state": self.backend.state(),        # Mock 剧本游标,可复放
            "task": {"goal": task.goal, "files_hint": task.files_hint,
                     "follow_up_of": task.follow_up_of, "extra": task.extra},
            "context": {
                "goal": self.context.goal,
                "files_hint": self.context.files_hint,
                "memory_block": self.context.memory_block,
                "raw_turns": [_turn_to_dict(t) for t in self.context.raw_turns],
                "last_prune": {"before_tokens": self.context.last_prune.before_tokens,
                               "after_tokens": self.context.last_prune.after_tokens,
                               "pruned": self.context.last_prune.pruned,
                               "strategies": self.context.last_prune.strategies},
            },
            "workspace_fingerprint": self.workspace.snapshot(),   # {路径: SHA256} 全表
            "metrics": self.metrics.snapshot(),
        }
        self.checkpoint.save(task.task_id, snap)
        self.logger.info("checkpoint: task=%s step=%s reason=%s", task.task_id, step, reason)
        self._emit({"type": "checkpoint", "step": step, "reason": reason,
                    "task_id": task.task_id, "ts": now_iso()})
```

快照**完全自包含**（`checkpoint/store.py` docstring 的设计目标：「任意一处被中断都能从上次断点无损恢复」）：任务定义 + 已推进步数 + 完整上下文 + 工作区指纹 + 已累计指标 + 后端状态。

**落盘时机六种**：`run/resume`（启动即落）→ `interval`（每 4 步，相对恢复起点计数）→ `prune`（裁剪前强制）→ `interrupt`（Ctrl-C 或 `stop_after_steps`）→ `error`（异常保留现场）→ `final`（终局，interrupted/error 除外）。

存储层极薄（`checkpoint/store.py:30-44`）——「存什么、何时存」全部由 harness 决定：

```python
    def save(self, task_id: str, snapshot: dict) -> None:
        if not self.enabled:
            return
        snapshot = dict(snapshot)
        snapshot.setdefault("saved_at", now_iso())
        atomic_write(self.path(task_id), json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    def load(self, task_id: str) -> dict | None:
        p = self.path(task_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
```

`atomic_write`（`util.py:48-71`）：临时文件 + `os.replace`——「避免中途崩溃留下半截文件」；Windows 上病毒扫描/索引服务可能短暂占用目标文件，对 `PermissionError` 做 8 次有界重试（间隔 0.025s 递增）。

### 5.4.2 漂移识别（`checkpoint/drift.py:43-51`，全文件核心就这一个函数）

```python
class WorkspaceDriftDetector:
    @staticmethod
    def compare(before: dict[str, str], after: dict[str, str]) -> DriftReport:
        b_keys = set(before.keys())
        a_keys = set(after.keys())
        modified = sorted(k for k in (b_keys & a_keys) if before[k] != after[k])
        added = sorted(a_keys - b_keys)
        deleted = sorted(b_keys - a_keys)
        return DriftReport(modified=modified, added=added, deleted=deleted)
```

为什么必要（模块 docstring）：恢复时工作区可能已被外部修改（用户手改、git 操作、并发进程），Agent 基于的「旧文件摘要/旧读取结果」可能已失效——直接续跑会产生灾难性合并错误。三集合运算逐文件精确比对，识别准确率 100%（Layer 4 的 45 个场景验证）。

**设计取舍**（`eval/runner.py:498-500` 注释明示）：whitespace/reformat 这类「语义不变内容变」的场景也会被哈希精确比对检出（误报）——**宁可误报不可漏报**，漂移矩阵中显式测试这两类。

## 5.5 多轮编排闭环全流程（`agent/orchestrator.py`，逐行精读）

### 5.5.1 初始化与续跑分支（`agent/orchestrator.py:149-176`）

```python
    def run(self, goal: str | None = None, task_id: str | None = None) -> dict:
        task_id = task_id or ("orch-" + short_id())
        self._task_id = task_id
        self._used_tokens = 0
        self.memory = WorkingMemory()
        self.archive = RetryArchive(compress_fn=self._compress_failure)
        # 编排内共享交付工作区(跨编排隔离;Layer 7 检查器经 artifact["workspace"] 读取)
        self._shared_ws = (Path(self.config.get("workspace.root", "."))
                           / f".orch_{task_id}" / "ws")
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
```

注意共享工作区路径的构造：`<workspace.root>/.orch_<task_id>/ws`——**同一编排内共享、跨编排隔离**（批次④修正，注释明说 dep-chain 类 compound 目标依赖此语义）。

### 5.5.2 轮循环主体（`agent/orchestrator.py:178-227`）

```python
        success = False
        stop_reason = "达到最大轮数上限"
        round_no = start_round - 1
        for round_no in range(start_round, self.max_rounds + 1):
            self._round_no = round_no
            self._emit({"type": "orchestration_round_start", "task_id": task_id,
                        "round": round_no})
            self._execute_pending_tasks()                     # ① 执行所有就绪任务

            if self.validator is not None:                    # ② 验收
                try:
                    verdict = self.validator.verify(self._goal, self._checklist, self._tasks)
                except Exception as exc:
                    # 验收调用失败不炸编排:降级为未通过,缺失项回流下一轮重试验收
                    self._emit({"type": "orchestration_validate_error", "task_id": task_id,
                                "detail": f"{type(exc).__name__}: {exc}"[:200]})
                    verdict = ValidationVerdict(
                        completed=False,
                        missing_requirements=[f"验收调用失败,请重试验收: {type(exc).__name__}"])
            else:
                verdict = self._auto_verdict()                # 确定性模式:全 DONE 即过
            if verdict.completed and self._checklist.is_complete:   # ③ 双门判定
                success = True
                stop_reason = "Completion Checklist 验收通过"
                self._emit({"type": "orchestration_round_end", "task_id": task_id,
                            "round": round_no, "result": "accept"})
                self._write_snapshot(validated=True)
                break

            # ④ 未通过 → 缺失项精确回流(BLOCKED/FAILED 任务注记并入)
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
            # ⑤ 增量重规划(带活动日志) + 死局检测
            new_tasks = self.planner.replan(self._goal, self._tasks, missing,
                                            activity=self.memory.recent_activity(8))
            if not new_tasks and not any(t.status is TaskStatus.PENDING for t in self._tasks):
                stop_reason = "无 PENDING 任务且重规划未产出新任务,无法继续推进"
                break
            self._tasks.extend(new_tasks)
            self._sanitize_deps()
```

四个面试级细节：

1. **验收异常降级**：Validator 调用失败（网络/超时/输出不合法）不炸编排——降级为「未通过 + 验收调用失败请重试」的缺失项，下一轮重试验收。这是真实模型实测驱动的修复（Layer 7 首跑发现验收超时会炸整个编排）。
2. **双门判定** `verdict.completed and self._checklist.is_complete`：模型口头说完成**且**清单逐项满足才算过——单靠 LLM 自述一定被「乐观推断」击穿。
3. **缺失项注记的三种来源**：Validator 的 missing_requirements + BLOCKED 任务（「需规划绕行路径」）+ FAILED 任务（「需拆成更小步骤」）——回流给 Planner 的不是「没完成」而是**可执行的修复指令**。
4. **死局检测**：replan 没产出新任务且没有 PENDING 任务 → 提前终止，避免空转烧 token。

### 5.5.3 工作队列与预算熔断（`agent/orchestrator.py:250-273`）

```python
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
```

`while True` 工作队列的设计意图：串行分支每次只跑一个就绪任务然后**回到循环头**——失败任务在 `_handle_failure` 里转回 PENDING 后，本轮内就能被重新拾起（「失败任务轮内即时重入队」，重试与轮次解耦）。三种退出：预算熔断（PENDING 全转 BLOCKED）、无 PENDING、就绪集为空（依赖未满足 → 全部转 BLOCKED 并发 `subtask_blocked`）。

### 5.5.4 单任务全生命周期（`agent/orchestrator.py:309-357`）

```python
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
        task.token_usage = int(res.metrics.get("prompt_tokens_total", 0)) \
            + int(res.metrics.get("completion_tokens_total", 0))
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
```

状态映射表（面试背诵点）：

| 子任务运行结果 | 编排层处理 |
| --- | --- |
| completed（无控制动作） | DONE |
| completed + `submit_result(success=True)` | DONE |
| completed + `submit_result(success=False)` | FAILED → `_handle_failure`（可重试） |
| blocked / `request_block` | BLOCKED（等 replan 绕行） |
| max_steps / error / 异常 | FAILED → `_handle_failure` |

### 5.5.5 失败收口与重试重入队（`agent/orchestrator.py:359-373`）

```python
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
```

`attempts <= max_retries` 的语义（默认 max_retries=2）：任务最多执行 **3 次**（1 次初始 + 2 次重试）——`attempts` 在 `transition(RUNNING)` 时自增（`tasks.py:62-63`）。重试的「学费」来自 `archive.archive()`：失败轨迹经 `compress_fn` 压缩为教训（LLM 模式用 `FAILURE_COMPRESS_PROMPT` 压成「根因+下次策略」≤250 字，异常回退 `truncate(failure, 2000)`），下次 `_run_single` 开头 `render_for_task` 取出注入上下文。

### 5.5.6 子任务 harness 的装配：共享与隔离的边界（`agent/orchestrator.py:400-424`）

```python
    def _build_harness(self, task: Task, backend):
        from ..safety import AllowAllProvider
        from .harness import AgentHarness
        cfg = Config(self.config.to_dict())
        # 同一编排内的子任务共享一个交付工作区(批次④修正):目标级产物落在同一
        # 目录,后续任务可直接使用先任务的产出(dep-chain 类 compound 目标依赖此
        # 语义);跨编排仍完全隔离。记忆/工件按子任务隔离,断点键含子任务 id 天然隔离。
        base = Path(self.config.get("workspace.root", ".")) / f".orch_{self._task_id}"
        cfg.set("workspace.root", str(self._shared_ws))
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
```

五条边界，一句话记住：**工作区共享、记忆与工件隔离、断点键隔离、观测汇流、白名单收窄**。`allowed_tools = set(allow) | CONTROL_TOOLS`——控制动作**恒在白名单**，防止配置出「无法收口」的角色。每子任务独立 `Config` 副本 + 独立 `SafetyGuard`/`RepeatedActionGuard` 实例——并行子任务下指纹状态天然隔离（测试 `test_working_memory.py` 用 8 线程并发验证）。

### 5.5.7 编排快照与续跑（`orchestrator/snapshot.py` 全文逻辑）

```python
def snapshot_key(task_id: str) -> str:
    return f"{task_id.replace('/', '_')}-orchestration"      # 复用同一 CheckpointStore

def snapshot_to_dict(goal, round_no, validated, tasks, checklist, records) -> dict:
    return {
        "version": SNAPSHOT_VERSION,
        "goal": goal,
        "round_no": round_no,
        "validated": validated,
        "tasks": [t.to_dict() for t in tasks],               # 任务全量(状态/尝试/结论/依赖)
        "checklist": checklist.to_dict(),
        "archive": [asdict(r) for r in records],             # Retry Archive 已压缩记录
    }

def restore_state(raw) -> tuple[str, int, bool, list[Task], CompletionChecklist, list[RetryRecord]]:
    goal = str(raw["goal"])
    round_no = int(raw.get("round_no", 0))
    validated = bool(raw.get("validated", False))
    tasks = [Task.from_dict(d) for d in raw.get("tasks", [])]
    checklist = CompletionChecklist.from_dict(raw.get("checklist", {}))
    records = [RetryRecord(**r) for r in raw.get("archive", [])]
    return goal, round_no, validated, tasks, checklist, records
```

**两层 checkpoint 的语义差异**（面试高频）：

| | 单任务 checkpoint | 编排快照 |
| --- | --- | --- |
| 键 | `<task_id>` | `<orch_id>-orchestration`（同一 CheckpointStore） |
| 粒度 | 步级（含 backend 游标、完整上下文） | 任务/轮级（不含子任务轨迹） |
| 恢复语义 | 从 step_index+1 无损续接 | validated=True 从下一轮继续；False 重做本轮（DONE 任务不重跑） |
| 写入时机 | start/interval/prune/interrupt/error/final | 编排开始、每子任务结束、每轮驳回后、验收通过 |

设计要点（`snapshot.py` docstring）：子任务原始执行轨迹由子任务自身 checkpoint 承载——快照轻量、恢复语义清晰。已知边界（MERGE_DESIGN 开放点 O1）：编排 resume 对「崩溃时 RUNNING 的子任务」采取**整任务重跑**（其快照里仍是 PENDING），不自动步级续接子任务断点。`Task.from_dict` 恢复时**绕过状态机校验**直接重建（`tasks.py:84-85` 注释：「快照恢复用:按已保存的状态直接重建(不经状态机校验)」）——快照里的状态组合是历史事实，恢复要求「原样重建」而非「重新走一遍合法路径」。

### 5.5.8 确定性退化（`agent/orchestrator.py:375-387`）

```python
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
```

`planner_mode=deterministic`（默认）时零 LLM：单任务单轮、全 DONE 即过——不配 LLM 时行为与单 Agent 底座完全一致，零成本向后兼容。已知边界：`_auto_verdict` 只看状态不看内容，空终答的子任务（status=completed、final_answer 为空）在此模式下会被放行（LLM 模式的 Validator 双门会拦）——见附录 B 第 8 条。

## 5.6 状态机硬约束（`orchestrator/tasks.py:11-63`，全量源码）

```python
class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


# 合法迁移表。FAILED → PENDING 用于有重试额度时的归档重注入;
# PENDING → BLOCKED 用于依赖未满足或全局预算耗尽时任务无法启动即阻塞。
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.BLOCKED},
    TaskStatus.RUNNING: {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.BLOCKED},
    TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.FAILED},
    TaskStatus.FAILED: {TaskStatus.PENDING},
    TaskStatus.DONE: set(),
}


class IllegalTransitionError(Exception):
    """非法状态迁移。"""


class Task:
    def transition(self, new_status: TaskStatus) -> None:
        allowed = ALLOWED_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise IllegalTransitionError(
                f"任务 {self.id} 非法迁移: {self.status.value} → {new_status.value},"
                f"允许的迁移: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
            )
        self.status = new_status
        if new_status == TaskStatus.RUNNING:
            self.attempts += 1
```

三条特殊边各有注释出处：`FAILED→PENDING`（重试重注入）、`PENDING→BLOCKED`（无法启动即阻塞）、`BLOCKED→RUNNING`（迁移表里存在但当前代码从未触发——BLOCKED 任务只能等 replan 产出新任务绕行）。非法迁移的报错信息包含**当前状态、目标状态与允许项列表**——测试 `test_state_machine.py:39-44` 专门断言这条消息。

## 5.7 Web API 与 SSE 实时链路（逐行对照 `api/`）

### 5.7.1 事件桥（`api/event_bus.py` 全文 54 行）

```python
_DONE = {"type": "__done__"}

class TaskEventBus:
    """每任务一个队列的事件总线,供 SSE / 轮询消费。"""

    def __init__(self) -> None:
        self._queues: dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def register(self, task_id: str) -> queue.Queue:
        """为某任务创建事件队列;需在后台 worker 启动之前调用。"""
        with self._lock:
            q: queue.Queue = queue.Queue()
            self._queues[task_id] = q
            return q

    def on_event(self, event: dict) -> None:
        """harness 事件回调:按 task_id 推入对应队列。"""
        tid = event.get("task_id")
        if not tid:
            return
        q = self._queues.get(tid)
        if q is not None:
            q.put_nowait(event)

    def done(self, task_id: str) -> None:
        """worker 结束时推送哨兵事件,通知 SSE 流关闭。"""
        q = self._queues.get(task_id)
        if q is not None:
            q.put_nowait(_DONE)
```

设计要点：**无事件类型白名单**——新增事件类型天然可达 SSE；`register` 必须在 worker 启动前调用（防丢首批事件）；哨兵是普通 dict，与业务事件同队列传递。

### 5.7.2 后台执行与 SSE 生成器（`api/fastapi_server.py:66-103, 177-200`）

```python
def _worker(task_id: str, task_data: dict, config: Config, bus: TaskEventBus) -> None:
    """后台线程:跑真实的 harness 并把语义事件推给事件总线。"""
    from ..agent import AgentHarness
    from ..safety import AllowAllProvider

    cfg = Config(config.to_dict())
    # SSE 已经是实时追踪,不必再写 trace.json(保持 API 运行目录干净)
    cfg.set("observability.enabled", False)

    def _on_event(event: dict) -> None:
        event = dict(event)
        event.setdefault("task_id", task_id)  # harness 部分事件不带 task_id,这里补全
        bus.on_event(event)
        _RUNS[task_id]["events"].append(event)

    try:
        backend_name = _decide_backend(config, task_data)
        _RUNS[task_id]["backend"] = backend_name  # 尽早回填,列表立即可见
        backend = _build_backend(cfg, task_data, backend_name)
        harness = AgentHarness.build(cfg, backend=backend,
                                     approver=AllowAllProvider(), on_event=_on_event)
        for rel, content in (task_data.get("setup_files") or {}).items():
            harness.workspace.write_text(rel, content)
        task = TaskInput(task_id=task_id, goal=task_data.get("goal", ""),
                         files_hint=task_data.get("files_hint", []),
                         follow_up_of=task_data.get("follow_up_of"))
        result = harness.run(task)
        _RUNS[task_id]["status"] = result.status
        _RUNS[task_id]["result"] = {
            "status": result.status,
            "final_answer": result.final_answer,
            "metrics": result.metrics,
        }
    except Exception as exc:  # 后台线程异常不能冒泡到事件循环,需记录下来
        _RUNS[task_id]["status"] = "error"
        _RUNS[task_id]["error"] = str(exc)
    finally:
        bus.done(task_id)          # ← 哨兵必达,保证 SSE 流能正常收尾
```

```python
    @app.get("/api/run/{task_id}/events")
    async def api_events(task_id: str):
        q = bus.get(task_id)
        if q is None:
            return JSONResponse({"error": "no such task or stream already ended"},
                                status_code=404)
        loop = asyncio.get_event_loop()

        async def gen():
            # 不用 Request 注入(规避部分 pydantic 版本的 TypeAdapter 重建问题);
            # 以队列哨兵(__done__)结束流,并以心跳保活。客户端断开时队列不再被消费,
            # 但 sentinel 仍会触发正常结束,不会泄漏事件循环。
            while True:
                try:
                    evt = await loop.run_in_executor(None, lambda: q.get(timeout=15))
                except Empty:
                    yield ": keep-alive\n\n"          # SSE 注释行做心跳
                    continue
                if evt.get("type") == "__done__":
                    yield "event: done\ndata: {\"type\":\"done\"}\n\n"   # 具名事件
                    break
                yield f"data: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")
```

SSE 三件套：**哨兵**（`__done__` → 具名 `done` 事件 → 前端 `addEventListener('done')` 关流）、**心跳**（`q.get(timeout=15)` 超时发 `: keep-alive` 注释行，防代理断连）、**后台线程隔离**（阻塞 get 扔进 executor，不卡事件循环；异常不冒泡，`finally` 保证哨兵必达）。

### 5.7.3 一键双跑对照（`api/fastapi_server.py:39-51, 135-154`）

```python
def _decide_backend(config: Config, task_data: dict) -> str:
    """决定本任务用哪个后端(纯决策不构造实例)。

    优先级:存在 script 一律锁定 mock(离线回放,历史行为);
           其次请求显式指定的 backend 字段;
           缺省则跟随服务端配置的 model.backend。
    """
    if task_data.get("script") is not None:
        return "mock"
    choice = task_data.get("backend")
    if choice in _VALID_BACKENDS:
        return choice
    return config.model_backend
```

```python
    @app.post("/api/compare")
    def api_compare(task: dict):
        goal = (task.get("goal") or "").strip()
        if not goal:
            return JSONResponse({"error": "双跑对比需要非空 goal"}, status_code=400)
        compare_id = "cmp-" + uuid.uuid4().hex[:8]
        common = {"goal": goal}
        if task.get("follow_up_of"):
            common["follow_up_of"] = task["follow_up_of"]
        if task.get("setup_files"):
            common["setup_files"] = task["setup_files"]
        mock_arm = dict(common, task_id=f"{compare_id}-mock",
                        backend="mock", answer=task.get("answer", "任务已完成。"))
        if task.get("script"):
            mock_arm["script"] = task["script"]
        real_arm = dict(common, task_id=f"{compare_id}-local_openai",
                        backend="local_openai")
        ids = [_launch(mock_arm, arm="mock", compare_group=compare_id)["task_id"],
               _launch(real_arm, arm="local_openai", compare_group=compare_id)["task_id"]]
        return {"compare_id": compare_id, "task_ids": ids}
```

「compare_group 怎么共享」的答案就在这：两臂各自调用一次公共提交通道 `_launch(task_data, *, arm, compare_group)`，同一 `compare_id` 写进各自的 `_RUNS` 记录，`/api/runs` 与 `/api/run/{id}` 都回显 `arm` 与 `compare_group`。两臂**并行执行**（各自独立线程）。前端只对真实臂开 SSE，mock 臂靠 2 秒轮询渲染成对照表。

## 5.8 评测数据流（七层 + 三种对照）

评测的总原则（`eval/runner.py` docstring）：**刻意分离「模型能力」与「系统能力」**。Layer 1-5 全部用 MockBackend 脚本回放——同一份脚本输入下，唯一变量是 harness 开关，量到的是系统能力；模型能力单独由 Layer 6/6b/7 在固定模型与任务集上评估。通过判定统一用 `_PASS_THRESHOLD=0.9` 的 X/Y 通过率而非二值 100%——「指标退化可被察觉」。

| 层 | 评测对象 | 数据规模 | 核心口径 |
| --- | --- | --- | --- |
| 1 | Harness 回归（完成/拦截/工件齐全） | 手写 17 + 冻结 15 = 32 | 硬断言 + 三类工件齐全，pass_rate≥0.9 |
| 2 | 上下文治理（治理 vs 不治理 vs 贴边） | 16 任务 | 压缩率>0、预算内 100%、**信息保留率 100%**（probe 探针）、硬限额合规 |
| 3 | 记忆收益（fresh/stale/missing/wrong_hit 四场景矩阵） | 16 任务 | fresh 重读=0、stale 读到新内容且哈希刷新、wrong 不误用诱饵 |
| 4 | 恢复正确性 + 漂移识别 | 45 场景 | 识别准确率≥0.9、恢复完成率≥0.9、large_scale ≤10s |
| 5 | 检索召回（四类查询分判） | 82 条 | recall@1/3/5 + MRR@5，要求 hybrid@3 严格优于 substring |
| 6 | 真实模型端到端 + LLM judge | 4 编码任务 | completed ∧ 硬断言 ∧ judge.passed 三者与 |
| 6b | 裸基线三臂对照 | 同任务集 × 2 臂 | 与 Layer 6 同源断言；`ok` 仅表示「测量完成」 |
| 7 | 多智能体端到端 + 机制消融 | 8 任务 | **客观检查器**（真实 subprocess 执行产物并断言）∧ agent 自报成功；退出码全过才 0 |

**三种「对照」各司其职**（面试高频）：

1. **系统开关 A/B**（runner 内部）：`Config(base.to_dict())` 克隆后只改一个键——治理 1500/3 vs 基线 10M/1000 vs 贴边 600/2；memory_enabled=False 对照臂；detect_drift=False 对照臂。
2. **有无框架三臂**（`raw_baseline.py`）：single_shot（单次调用+代码块提取落盘）/ naive_loop（朴素工具循环，**刻意不复用**治理/记忆/断点/安全审批/去重，只留 Workspace 边界与 5 个文件工具）/ harness（复用 Layer 6 报告不重跑）。实测（qwen3.5:2b 硬断言）：single_shot 1/4 → naive_loop 3/4 → harness 4/4；代价是 prompt token 529 → 14,564 → 115,919——**框架的钱花在哪、值不值，两组数字同时摆出来**。
3. **机制消融**（`layer7 --ablate guard,retry,budget,validator`）：把单机制放宽到永不触发，量化每个机制的边际贡献。

**回归灵敏度锚**：`test_eval.py` 故意注入退化（关掉记忆、关掉漂移检测），断言对应指标必须显著下降——防止评测变成「怎么跑都绿」的自证闭环。

**结果边界（如实标注，README 同款）**：Layer 1-5 与全部 pytest 用 MockBackend 离线回放，度量系统能力不代表模型能力；Layer 6 的 LLM 评委由 2b 小模型担任，实测 0/4 通过、判定不可靠，结果如实保留不以硬断言冒称评委通过；Layer 7 首次真实实测 quick 套件 3/4（hello/notes/calc 过，fizzbuzz 因 thinking 模型冗长思考被 max_tokens 截断——判定为小模型能力边界而非管道缺陷）。
## 5.9 工件沉淀与 CLI 装配（`artifacts.py` + `cli.py` 精读）

「跑完说不清发生了什么」由这一站兜底。三类工件对应「结果可复盘」诉求（`artifacts.py` docstring）：**trajectory.jsonl**（逐步追加的完整轨迹，任何时刻崩溃都能复盘）、**checkpoint.json**（可恢复断点聚合进工件目录）、**metrics.json + report.md**（聚合指标与人类可读报告）。

### 5.9.1 Metrics — 指标累加器（`artifacts.py:22-77`）

```python
@dataclass
class Metrics:
    """运行期指标累加器(线程不安全,单进程顺序使用)。"""

    steps: int = 0
    tool_calls: int = 0
    read_calls: int = 0
    read_cache_hits: int = 0          # 去重/记忆短路命中的读次数
    write_calls: int = 0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    cost_usd: float = 0.0            # 若配置了 model.pricing 则累计,否则为 0
    prompt_budget_tokens: int = 0
    latency_ms_total: int = 0
    prunes: int = 0
    compression_ratios: list = field(default_factory=list)
    files_remembered: int = 0
    memory_queries: int = 0
    denied_actions: int = 0
    skipped_repeats: int = 0

    def snapshot(self) -> dict:
        return {
            …
            "cost_usd": round(self.cost_usd, 6),
            "avg_prompt_tokens": round(self.prompt_tokens_total / self.steps, 2) if self.steps else 0,
            "avg_compression_ratio": round(self.avg_compression_ratio(), 4),
            "max_compression_ratio": round(self.max_compression_ratio(), 4),
            "denied_actions": self.denied_actions,
            "skipped_repeats": self.skipped_repeats,
        }
```

16 个累加字段覆盖四类故事：**效率**（steps/tool_calls/token/成本/延迟）、**治理**（prunes/compression_ratios——安全层的 `read_cache_hits/skipped_repeats/denied` 由 `_sync_guard_metrics` 同步进来）、**记忆**（files_remembered/memory_queries）。`snapshot()` 派生均值（avg_*），`prompt_under_budget` 用「平均每步 prompt ≤ 预算」近似软预算合规。

### 5.9.2 RunRecorder — 崩溃可复盘的轨迹

```python
class RunRecorder:
    """轨迹记录器:逐行追加写 trajectory.jsonl,崩溃可恢复。"""

    def record(self, obj: dict) -> None:
        text = json.dumps(obj, ensure_ascii=False, default=str)
        if self.redactor is not None:
            text = self.redactor.redact(text)        # 每行写前脱敏
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text + "\n")                     # 追加写:崩溃只丢最后一行
        self._count += 1
```

逐行**追加**（而非攒在内存最后一次性写）——「任何时刻崩溃都能复盘已发生的事」。每行 JSON 过 Redactor。

### 5.9.3 report.md 的耗时时间线（`artifacts.py:208-234`）

```python
def _build_timeline(task_dir: Path | None) -> list[dict]:
    """从 trajectory.jsonl 重建逐步耗时时间线(零额外存储,只读既有工件)。"""
    …
    for line in p.read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        t = ev.get("type")
        if t == "model_call":
            rows.append({"index": ev.get("index"), "kind": "model_call",
                         "latency_ms": ev.get("latency_ms", 0),
                         "prompt_tokens": ev.get("prompt_tokens", 0),
                         "completion_tokens": ev.get("completion_tokens", 0)})
        elif t == "tool_call":
            rows.append({"index": ev.get("step_index"), "kind": f"tool:{ev.get('name')}",
                         "latency_ms": ev.get("latency_ms", 0), …})
```

设计巧思：时间线**不新增任何存储**——报告渲染时从 trajectory.jsonl 反推（零额外存储，只读既有工件）。report.md 的章节结构：状态/步数/token/成本 → 上下文治理（平均/最高压缩率、裁剪次数）→ 工具与记忆（读/缓存命中/写/沉淀/拦截/重复跳过）→ 耗时时间线表 → 最终回答引用。所有导出统一过 Redactor（`export()` 与 `_render_report` 末尾各一次）。

### 5.9.4 cli.py — 入口的装配纪律（236 行全读要点）

```python
def _build_config(args) -> Config:
    cfg = Config.load(getattr(args, "config", None))
    if getattr(args, "hitl_policy", None):
        cfg.set("safety.hitl_policy", args.hitl_policy)
    if getattr(args, "workspace", None):
        cfg.set("workspace.root", args.workspace)
    if getattr(args, "backend", None):
        cfg.set("model.backend", args.backend)
    return cfg


def _make_backend(cfg: Config, task_data: dict):
    """优先用任务文件里的 script 构造 mock;否则按 config 后端装配。"""
    if task_data.get("script"):
        return MockBackend(script=task_data["script"],
                           default_answer=task_data.get("answer", "任务已完成。"))
    return create_backend(cfg)


def cmd_run(args) -> int:
    …
    cfg = _build_config(args)
    data = load_task_file(args.task_file)
    backend = _make_backend(cfg, data)
    policy = cfg.get("safety.hitl_policy", "prompt")
    approver = {"allow": AllowAllProvider(), "deny": DenyAllProvider()}.get(policy)
    harness = AgentHarness.build(cfg, backend=backend, approver=approver)
    task = TaskInput(task_id=data.get("task_id", Path(args.task_file).stem), …)
    # 预置 setup_files(演示/评测用)
    for rel, content in (data.get("setup_files") or {}).items():
        harness.workspace.write_text(rel, content)
    result = harness.run(task)
    print(json.dumps({"task_id": result.task_id, "status": result.status,
                      "metrics": result.metrics,
                      "final_answer": result.final_answer,
                      "artifacts_dir": str(harness.artifacts.task_dir(result.task_id))}, …))
    return 0 if result.status == "completed" else 1
```

三个入口纪律：CLI 覆盖项经 `cfg.set` **后打**在配置上（优先级：命令行 > YAML > DEFAULT）；带 `script` 的任务一律 Mock（`policy` 取不到 prompt 时 `approver` 为 None，`SafetyGuard` 内部 `_default_approver` 兜底为 PromptProvider）；非 completed 退出码 1（shell 可判）。`cmd_orchestrate` 的关键一行：`failed = (result.get("summary") or {}).get("failed", 0); return 0 if failed == 0 else 1`——编排的退出码锚定失败子任务数。`cmd_eval` 的退出码锚定 `all(r.get("ok"))`——**评测不过 = 命令失败**，这是评测能当 CI 门禁的前提。
## 5.10 端到端事件演练：一次「驳回→重规划→二轮通过」的全部事件流

这是 5.5 节代码的动态视图。场景：编排目标「创建配置模块并写使用说明」，Planner 拆出 T1，第一轮 T1 执行成功但 Validator 驳回（缺 checklist 项），replan 增补 T2，第二轮通过。以下是从 `on_event` 总线上抓到的完整事件序列（SSE/trace.json 的同源数据，`…` 处省略重复字段）：

```json
{"type": "orchestration_start", "task_id": "orch-a1b2c3d4",
 "subtasks": ["T1"], "goal": "创建配置模块并写使用说明"}

{"type": "orchestration_plan", "task_id": "orch-a1b2c3d4",
 "tasks": ["T1:创建 config.py 与 config.md"], "checklist_items": 2}

{"type": "orchestration_round_start", "task_id": "orch-a1b2c3d4", "round": 1}

{"type": "subtask_start", "task_id": "orch-a1b2c3d4", "sub": "T1",
 "title": "创建 config.py 与 config.md"}

  # —— 子任务内部事件,带 sub 标签透传(_build_harness 的 _sub_event 闭包)——
  {"type": "task_start", "task_id": "orch-a1b2c3d4/T1", "sub": "T1", "reason": "run"}
  {"type": "step_start", "sub": "T1", "index": 0}
  {"type": "model_call", "sub": "T1", "index": 0, "model": "qwen3.5:2b",
   "prompt_tokens": 512, "completion_tokens": 88, "latency_ms": 8110}
  {"type": "tool_call", "sub": "T1", "step_index": 0, "name": "file_write",
   "status": "ok", "latency_ms": 2}
  {"type": "step_end", "sub": "T1", "index": 0}
  {"type": "task_end", "task_id": "orch-a1b2c3d4/T1", "sub": "T1", "status": "completed"}

{"type": "subtask_end", "task_id": "orch-a1b2c3d4", "sub": "T1", "status": "DONE"}

{"type": "orchestration_validated", "task_id": "orch-a1b2c3d4",
 "completed": false, "unmet_items": 1,
 "missing": ["Checklist 未满足: config.md 中给出 config.py 的使用示例"],
 "summary": "config.py 已创建且可导入,但使用说明文件未产出"}

{"type": "orchestration_round_end", "task_id": "orch-a1b2c3d4", "round": 1,
 "result": "reject",
 "missing": ["Checklist 未满足: config.md 中给出 config.py 的使用示例"]}

{"type": "orchestration_replan", "task_id": "orch-a1b2c3d4",
 "analysis": "T1 产出 config.py 但遗漏使用说明,增补独立说明任务",
 "new_tasks": ["T2"]}

{"type": "orchestration_round_start", "task_id": "orch-a1b2c3d4", "round": 2}

{"type": "subtask_start", "task_id": "orch-a1b2c3d4", "sub": "T2", "title": "补写 config.md"}
  … (T2 执行,期间可读取共享工作区里 T1 的 config.py)
{"type": "subtask_end", "task_id": "orch-a1b2c3d4", "sub": "T2", "status": "DONE"}

{"type": "orchestration_validated", "task_id": "orch-a1b2c3d4",
 "completed": true, "unmet_items": 0, "missing": [],
 "summary": "两任务产出齐全,checklist 全部满足"}

{"type": "orchestration_round_end", "task_id": "orch-a1b2c3d4", "round": 2,
 "result": "accept"}

{"type": "orchestration_end", "task_id": "orch-a1b2c3d4",
 "summary": {"total": 2, "completed": 2, "failed": 0, "blocked": 0,
             "failed_ids": [], "final_answers": {"T1": "…", "T2": "…"}}}
```

对照源码读这条流，每一段都有唯一出处：

| 事件段 | 代码出处 | 伴随动作 |
| --- | --- | --- |
| orchestration_start / plan | `run()` :174-175 + `PlannerRole.plan` 末尾 `_emit` | `plan()` 产出 tasks+checklist，随后 `_sanitize_deps()` + 落快照(validated=False) |
| round_start | `run()` :183-184 | — |
| subtask_start → 子任务事件 → subtask_end | `_run_single` :310-357 | 状态机 RUNNING(attempts+1)、Retry 教训注入、子任务事件加 `sub` 标签 |
| orchestration_validated | `ValidatorRole.verify` 末尾 `_emit` | `apply_verdict` 写回清单 + 确定性补齐 missing |
| round_end(result=reject) | `run()` :216-217 | 落快照(validated=False) |
| orchestration_replan | `PlannerRole.replan` 末尾 `_emit` | 新任务 id 续号、复用旧 id 丢弃、`_sanitize_deps()` 复查 |
| round_end(result=accept) | `run()` :202-203 | 落快照(validated=True) → break |
| orchestration_end | `run()` :239 | `_export()` 写 orchestration.json |

**三种异常分支在这条流上的样子**（同一位置替换）：

- **失败重试**：`subtask_end {status:"FAILED"}` 之后紧跟 `task_retry_scheduled {task, attempt, lessons}`（教训文本就在事件里），随后该任务再次 `subtask_start`——S6 场景断言第二次尝试的模型输入含 "Retry Archive"。
- **预算熔断**：`orchestration_round_start` 之前/工作队列开头直接 `budget_exceeded {task: "T2"}`，PENDING 全转 BLOCKED（`_execute_pending_tasks` :252-260）。
- **验收调用失败**：`orchestration_validate_error {detail: "TimeoutError: …"}` 替代 orchestration_validated，verdict 降级为未通过——编排不死。

**对应的 trace.json**（Tracer 消费同一事件流的产物）：编排层事件不进 Tracer（Tracer 挂在单任务 harness 上），但每个子任务各有自己的 `trace.json`（span 树 `run → step:0 → model_call/tool:file_write`），加上编排级的 `orchestration.json`（checklist/subtasks/activity/共享工作区路径）——**三层工件拼出完整复盘视图**：编排层看「谁做了什么、验收为什么过/不过」，子任务层看「每一步的模型与工具行为」，指标层看「花了多少 token 与钱」。
## 5.11 真实模型评测与统一断言（`eval/real.py` + `runner._check_expect` 精读）

Layer 1-5 的判定入口只有一个函数——`EvalRunner._check_expect`（`eval/runner.py:208-285`），Layer 6 复用它（`real.py:89`），Layer 6b 的两条裸基线臂也复用它。**一份断言代码，三层评测口径统一**，这是评测体系最值得学的设计。全文精读：

```python
    @staticmethod
    def _check_expect(result: RunResult, harness, task: dict) -> tuple[bool, list[str]]:
        msgs: list[str] = []
        ok = True
        exp = task.get("expect", {})

        # 1) 运行状态白名单:负例同样要求 mock 轨迹优雅走到终答(不崩溃)
        allowed = exp.get("status_in", ["completed"])
        if result.status not in allowed:
            ok = False
            msgs.append(f"状态不在 {allowed}: {result.status}")

        calls = [c for s in result.steps for c in s.tool_calls]

        # 2) 负例:指定工具必须被拦截/报错,且拦截原因非空
        sfc = exp.get("should_fail_call")
        if sfc:
            for name in ([sfc] if isinstance(sfc, str) else sfc):
                bad = [c for c in calls
                       if c.name == name and c.status in ("denied", "error")]
                if not bad:
                    ok = False
                    msgs.append(f"负例未拦截: {name}")
                elif not any(c.error for c in bad):
                    ok = False
                    msgs.append(f"拦截缺少原因: {name}")

        # 3) 边界:去重缓存命中(重复调用被短路)
        chc = exp.get("cache_hit_call")
        if chc and not any(c.name == chc and c.meta.get("cache_hit") for c in calls):
            ok = False
            msgs.append(f"未观察到缓存命中: {chc}")

        # 4) 文件断言
        for f in exp.get("files_created", []):
            if not harness.workspace.resolve(f).exists():
                ok = False
                msgs.append(f"文件未创建: {f}")
        for f in exp.get("no_files_created", []):
            try:
                exists = harness.workspace.resolve(f).exists()
            except Exception:
                # 路径本就指向工作区之外(如 ../evil.txt):检查其外部落点
                exists = (harness.workspace.root / f).resolve().exists()
            if exists:
                ok = False
                msgs.append(f"不应存在的文件被创建: {f}")
        for f, sub in (exp.get("file_contains") or {}).items():
            content = harness.workspace.read_text(f) or ""
            if sub not in content:
                ok = False
                msgs.append(f"文件内容不含 {sub!r}: {f}")
        for f, sub in (exp.get("file_not_contains") or {}).items():
            content = harness.workspace.read_text(f) or ""
            if sub in content:
                ok = False
                msgs.append(f"文件内容不应含 {sub!r}: {f}")
        for f, exact in (exp.get("file_equals") or {}).items():
            content = harness.workspace.read_text(f)
            if content != exact:
                ok = False
                msgs.append(f"文件内容与预期不一致: {f}")
        # 编辑精确性:除目标变更外,保留区域标记必须原样存在
        for f, marker in (exp.get("file_unchanged_except") or {}).items():
            content = harness.workspace.read_text(f) or ""
            if marker not in content:
                ok = False
                msgs.append(f"编辑破坏了未涉及区域: {f} 缺 {marker!r}")

        # 5) 终答断言
        fc = exp.get("final_contains")
        if fc and fc not in result.final_answer:
            ok = False
            msgs.append(f"终答不含 {fc!r}")
        fn = exp.get("final_not_contains")
        if fn and fn in result.final_answer:
            ok = False
            msgs.append(f"终答不应含 {fn!r}")
        return ok, msgs
```

五组断言对应任务三种 `kind`（positive/negative/boundary）：正例查「做出来了」（files_created/file_contains/final_contains），负例查「拦得漂亮」（should_fail_call 且**拦截原因非空**——拒绝必须可解释），边界查「短路真的发生」（cache_hit_call 检查 `meta.cache_hit`）。两个细节体现严谨：`no_files_created` 对逃逸路径检查**外部落点**（`../evil.txt` 的 resolve 会抛异常，改查 `root/../evil.txt` 是否真的存在）；`file_unchanged_except` 用保留区域标记验证**编辑没有误伤**（file_edit 唯一匹配纪律的行为级验收）。

### 5.11.2 RealTaskRunner — 真实模型的三重与判定（`eval/real.py`）

```python
    def _run_one(self, task: dict) -> dict[str, Any]:
        task_id = task["task_id"]
        workdir = self.output_dir / "workspaces" / task_id
        cfg = Config(self.base_config.to_dict())
        cfg.set("workspace.root", str(workdir / "workspace"))
        cfg.set("memory.root", str(workdir / "memory"))
        cfg.set("checkpoint.root", str(workdir / "checkpoints"))
        cfg.set("artifacts.root", str(workdir / "artifacts"))
        cfg.set("safety.hitl_policy", "allow")          # 无人值守:审批自动放行
        start = time.monotonic()
        …
        try:
            backend = self.backend_factory(cfg)
            harness = AgentHarness.build(cfg, backend=backend, approver=AllowAllProvider())
            for rel, content in (task.get("setup_files") or {}).items():
                harness.workspace.write_text(rel, content)
            result = harness.run(TaskInput(task_id=task_id, goal=task.get("goal", ""),
                                           files_hint=task.get("files_hint", [])))
            assertion_ok, assertion_messages = EvalRunner._check_expect(result, harness, task)
            snapshot = {}
            for rel in harness.workspace.list_files():
                …
            judge_verdict = LLMJudge(jbackend).judge(
                task.get("goal", ""), snapshot, (task.get("judge") or {}).get("rubric", ""))
            metrics = dict(result.metrics or {})
            passed = result.status == "completed" and assertion_ok and judge_verdict.passed
```

判定是**三重与**：`status=="completed"`（跑完了）∧ `_check_expect`（硬断言）∧ `judge.passed`（评委否决项）。评委后端可独立配置（`eval.real.judge.{base_url,api_key,model}` 覆盖 + 独立超时）——评委可以与被评模型不是同一个。mock 后端下优雅 skip（`real.py:34-38` 返回 `{"ok": False, "skipped": True, summary: "真实评测需要 model.backend=local_openai"}`）——CI 零模型依赖的保证。

任务样例（`benchmarks/real_tasks.json` 的 rt01，字段示意）：`goal`「在 utils.py 中实现 sha256_text(text) 函数…」、`setup_files` 预置已有函数的 utils.py、`expect.file_contains: {"utils.py": "sha256_text"}`、`judge.rubric: "必须使用 hashlib.sha256,按 UTF-8 编码,返回 hexdigest,并保持现有函数可用。"`——硬断言查函数存在，评委按 rubric 查实现质量，两层各司其职。

报告聚合（`real.py:52-66`）：`ok = rate >= threshold(默认 0.5)`，透出 token/成本/耗时总量，写 `real_report.json`——Layer 6b 的 harness 臂直接加载这份报告做三臂对照（不重跑）。
## 5.12 装配工厂：create_backend 与 build_registry（`__init__.py` 全读）

两个工厂函数是「Config → 可运行组件」的最后一步，短小但值得全读——面试问「你的依赖注入怎么落地」时，这两个函数就是答案。

```python
# agentmuster/models/__init__.py:22-47
def create_backend(config) -> ModelBackend:
    """根据配置节 model.backend 装配后端。"""
    from ..config import Config
    if isinstance(config, dict):
        config = Config(config)                    # 宽容入口:dict 也能装配
    kind = config.model_backend
    if kind == "mock":
        return MockBackend(seed=config.get("model.mock.seed", 42))
    if kind == "local_openai":
        o = config.get("model.local_openai", {})
        return LocalOpenAIBackend(
            base_url=o.get("base_url", "http://127.0.0.1:8080/v1"),
            api_key=o.get("api_key", "local"),
            model=o.get("model", "qwen2.5-coder-7b"),
            temperature=o.get("temperature", 0.0),
            timeout_seconds=o.get("timeout_seconds", 60),
            max_retries=o.get("max_retries", 3),
            backoff_base=o.get("backoff_base", 0.5),
            backoff_cap=o.get("backoff_cap", 8.0),
            stream=o.get("stream", False),
            max_tokens=o.get("max_tokens"),
            protocol_fallback=bool(o.get("protocol_fallback", True)),
            truncation_self_heal=bool(o.get("truncation_self_heal", True)),
            max_tokens_ceiling=int(o.get("max_tokens_ceiling", 32768)),
        )
    raise ValueError(f"未知模型后端: {kind}(支持 mock / local_openai)")
```

```python
# agentmuster/tools/__init__.py:35-45
def build_registry(memory=None) -> ToolRegistry:
    """构建标准 7 工具注册表(工具自身无状态,memory 经 ToolContext 注入)。"""
    return ToolRegistry([
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        ListFilesTool(),
        GrepTool(),
        ShellExecTool(),
        MemoryQueryTool(),
    ])
```

三个设计要点：

- **未知后端直接抛错**（不静默回退 mock）——配置错误应该在装配时暴露，而不是跑到一半变成行为异常。
- **工具无状态、memory 经 ToolContext 注入**——`memory_query` 运行时从 ctx 拿记忆容器，注册表本身不持有，因此注册表可以全局复用、并行任务各自注入各自记忆。
- **控制工具不在此清单**——`build_registry` 只有 7 个内置工具；`submit_result/request_block` 由编排层追加（3.5 节），这是「默认面最小」原则。
***

# 第六部分：逐模块源码精读（12 站）

> 每站固定结构：为什么先写它 → 关键实现（真实源码逐段解读）→ 动手试一试 → 常见易错点 → 练一练。所有行号以 `main` 分支当前版本为准。**这是求职复习的核心章节：面试官追问到任何机制，你都应该能「翻到那几行代码」讲出来。**

## 第 1 站 · 地基：config / state / util / cost / tasks

**为什么先写它**：所有上层模块都从这一站取「数据契约」。不理解 `Config` 的合并语义与 `state.py` 的字段全集，后面每一步都会似懂非懂。

### 1.1 config.py — DEFAULT 字典与深合并

内置 DEFAULT 字典（`config.py:21-125`）穷举所有配置节，这里摘录最有信息量的三节（安全与编排，批次②③新增）：

```python
    "safety": {
        "hitl_policy": "prompt",
        "dedup_enabled": True,
        "redaction_enabled": True,
        # 重复/振荡动作 Guard(批次②,移植自 miniMaster):三重死循环检测
        "repeat_guard": {
            "enabled": True,
            "max_repeat": 2,
            "window_size": 12,
            "window_max": 4,
            "count_cache_hits": True,  # 去重缓存命中也计入指纹(检测反复重读式刷步)
        },
        "shell": {
            "allow_commands": [
                "echo", "ls", "dir", "pwd", "cat", "type", "find", "grep",
                "findstr", "git", "python", "python3", "mkdir", "touch",
            ],
            "deny_patterns": [
                r"rm\s+-rf", r"del\s+/[sq]", "format", "shutdown", "reboot",
                "curl", "wget", r"chmod\s+777", ":(){", r">\s*/dev",
            ],
        },
        "allow_write_outside_ext": [],
    },
    …
    # 多智能体编排(移植自 miniMaster):多轮「执行→验收→重规划」闭环;
    # deterministic 模式零 LLM 退化(单任务单轮,向后兼容),llm 模式启用角色闭环
    "orchestrator": {
        "planner_mode": "deterministic",  # deterministic | llm
        "max_rounds": 3,
        "max_retries": 2,
        "parallel": 1,
        "max_total_tokens": 800000,  # prompt+completion 全局预算;0 = 不限
        "roles": {
            "planner": {"model": "", "temperature": 0.2},    # model 空 = 用主后端
            "validator": {"model": "", "temperature": 0.0},
        },
    },
```

深合并（`config.py:128-136`）：

```python
def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并 override 到 base(返回新字典)。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out
```

`get/set` 点路径访问（`config.py:163-176`）：`get` 逐段下钻返回原始值（**没有集中式类型强转**，类型收敛由调用方防御式完成，如 `int(cfg.get("api.port", 8910))`）；`set` 中间节点自动 `setdefault`——CLI 的 `--backend/--hitl-policy/--workspace` 覆盖就是靠它后打在配置上。

一个关键细节：`config/default.yaml` 是 DEFAULT 的**超集**而非复刻（如 `harness.empty_answer_nudges`、`artifacts.sft_log`、`eval.real_baseline` 节只在 YAML 里；Ollama 预置 11434/qwen3.5:2b 与内置默认 8080/qwen2.5-coder-7b 不同）。YAML 注释明说：CLI/API 默认加载内置默认值，要用本文件请显式 `--config config/default.yaml`。

### 1.2 state.py — 纯 dataclass 状态模型

设计思路（模块 docstring）：「把消息/工具调用/工具结果/步/任务输入/运行结果做成纯数据类，**不包含任何 I/O**，便于序列化到 checkpoint、轨迹 JSONL 与评测比对。」核心是 `Message.to_openai()` 的协议还原（`state.py:27-56`）：

```python
    def to_openai(self) -> dict:
        """转为 OpenAI 兼容格式(供本地 OpenAI 后端使用)。"""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.role == "tool":
            # Tool 消息只需要 tool_call_id，不需要 name
            if self.tool_call_id:
                msg["tool_call_id"] = self.tool_call_id
        else:
            …
        if self.tool_calls:
            # Harness 内部使用扁平调用结构,发送给 OpenAI-compatible 服务时恢复
            # 标准的 type/function 包装,否则下一轮请求会被严格服务拒绝。
            calls = []
            for call in self.tool_calls:
                if "function" in call:
                    calls.append(call)
                    continue
                calls.append({
                    "id": call.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": call.get("name", ""),
                        "arguments": call.get("arguments", "{}"),
                    },
                })
            msg["tool_calls"] = calls
        return msg
```

Harness 内部用**扁平**调用结构（`{id, name, arguments}`）流转，发给 OpenAI 兼容服务时才包回 `{id, type:"function", function:{...}}`——不还原会被严格服务拒绝下一轮请求。五个模型一句话：`Message`（role/content/tool_calls）、`ToolCall`（status 五态：pending/ok/error/denied/skipped + meta 记 cache_hit/redacted）、`Step`（`prompt_before_tokens` 与 `prompt_tokens` 成对——评测压缩率的数据来源）、`TaskInput`（`extra` 是编排层下发 retry_lessons/allow_tools 的通道）、`RunResult`（status 五种 + `drift` + `control`）。

### 1.3 util.py — 小而关键的纯函数

四个高频件（`util.py`）：

```python
def truncate(text: str, max_chars: int, head_ratio: float = 0.6) -> str:
    """保守截断长文本:保留 head_ratio 比例的头部 + 尾部,便于保留关键信息。"""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * head_ratio)
    tail = max_chars - head - 30
    if tail < 0:
        return text[:max_chars]
    return text[:head] + f"\n…[截断 {len(text) - max_chars} 字符]…\n" + text[-tail:]

def clean_subprocess_env() -> dict:
    """子进程标准环境:剥覆盖率调试钩子 + 强制 UTF-8 stdio。…"""
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("COV_CORE_", "COVERAGE_")):
            env.pop(key)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env

def extract_json(text: str) -> dict:
    """从模型回复中尽力解析第一个合法 JSON 对象(裸 JSON / 代码块 / 首尾大括号兜底)。…"""
    if not text or not text.strip():
        raise ValueError("模型返回空内容,无法解析 JSON")
    candidates: list[str] = []
    fences = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    candidates += [f.strip() for f in fences]
    candidates.append(text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError(f"无法从模型回复中解析 JSON,原文片段: {text[:300]!r}")
```

`clean_subprocess_env` 的 docstring 是 CI 修复链的第一手史料：覆盖率环境变量遗传导致子进程 combine DataError（Linux CI 首跑实测）、Windows cp1252 中文乱码——两个真实事故浓缩在一个 10 行函数里。`extract_json` 的逐级候选（代码块 → 整段 → 首尾大括号）是小模型容错的地基；`parse_text_action`（`util.py:136-169`）是它的兄弟版，多一层 `<tool_call>/<function_call>` XML 标签解析（文本协议降级用）。

### 1.4 cost.py — 纯函数成本核算（39 行全读）

```python
    def cost_of(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """单次调用成本(美元)。未配置该模型时返回 0。"""
        rate = self.pricing.get(model) or self.pricing.get("*")
        if not rate:
            return 0.0
        input_per_1k = float(rate.get("input_per_1k", 0.0))
        output_per_1k = float(rate.get("output_per_1k", 0.0))
        return (prompt_tokens / 1000.0) * input_per_1k + \
            (completion_tokens / 1000.0) * output_per_1k
```

价目表 `model.pricing` 形如 `{"qwen2.5-coder-7b": {"input_per_1k": 0.0001, ...}}`，通配键 `*` 兜底；与调用链路正交（harness 每步调一次 `cost_of`）。

**动手试一试**：

```bash
python -m agentmuster doctor        # 看配置生效值:Python 版本/后端/工作区/硬上限/API 端口
python -m agentmuster artifacts --task-id demo_hello   # 列出某任务的工件
```

**常见易错点**：① 以为 `config/default.yaml` 是默认来源——内置 DEFAULT 才是；② 直接改 `cfg.get()` 返回的可变对象以为会生效——要 `cfg.set()`；③ 混淆 `budget_tokens`（软）与 `hard_limit_tokens`（硬）。

**练一练**：1) 写一个只有 `{"harness": {"max_steps": 5}}` 的 YAML，`Config.load` 后验证其余键仍是默认值；2) 手算 `estimate_tokens("你好 world")` 并与源码核对；3) 解释 `Step.prompt_before_tokens` 为什么必须在裁剪前记录（答：assemble 之后 before 已被覆盖，Step 要在模型调用前保存）。

## 第 2 站 · 模型后端：models/

**为什么先写它**：后端抽象是「确定性可复现」的根基。`ModelBackend` 统一接口让 Mock（验系统能力）与真实端点（验模型能力）互换且互不污染——`models/base.py` docstring：「这正是评测体系里『区分模型能力与系统能力』的落点。」

### 2.1 base.py — 抽象契约（60 行全读）

```python
@dataclass
class ModelResponse:
    """一次模型补全的统一返回。"""
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})

class ModelBackend(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, messages: list, tools: list[dict] | None = None,
                 temperature: float = 0.0) -> ModelResponse:
        """给定对话消息列表,返回补全结果(文本或工具调用)。"""

    def state(self) -> dict:
        """可 checkpoint 的后端状态(如脚本化后端的游标),默认空。"""
        return {}

    def load_state(self, state: dict) -> None:
        """恢复后端状态(Resume 用),默认无操作。子类按需覆盖。"""

    def tokenize_len(self, text: str) -> int:
        """粗粒度 token 估算,供后端记录 usage(重估策略见 context.tokens)。"""
        from ..context.tokens import estimate_tokens
        return estimate_tokens(text)
```

两个容易被忽略的钩子：`state()/load_state()`——后端可 checkpoint 的状态（Mock 剧本游标靠它续放），是 Resume 机制的隐藏功臣；`tokenize_len()`——usage 缺失时的兜底尺子。

### 2.2 mock.py — 脚本回放协议

```python
    def complete(self, messages: list, tools: list[dict] | None = None,
                 temperature: float = 0.0) -> ModelResponse:
        entry = (self.script[self._turn]
                 if self._turn < len(self.script)
                 else {"content": self.default_answer})     # 轮次用尽 -> 兜底防空转
        self._turn += 1

        entry = copy.deepcopy(entry)                        # 同一脚本对象可复用不污染
        prompt_tokens = self.tokenize_len(_join_for_estimate(messages))
        if "tool_calls" in entry:
            calls = []
            for c in entry["tool_calls"]:
                c = dict(c)
                c.setdefault("id", f"call_{self._call_seq}")   # 自动补调用 id
                self._call_seq += 1
                calls.append(c)
            return ModelResponse(
                content=entry.get("content", ""),
                tool_calls=calls,
                finish_reason="tool_calls",
                usage={"prompt_tokens": prompt_tokens, "completion_tokens": 10},
            )
        content = entry.get("content", self.default_answer)
        return ModelResponse(
            content=content,
            finish_reason="stop",
            usage={"prompt_tokens": prompt_tokens,
                   "completion_tokens": self.tokenize_len(content)},
        )
```

脚本语义：`script` 逐轮数组，`{"tool_calls": [...]}` 发起调用（finish_reason=tool_calls）或 `{"content": "终答"}` 终止。`state()` 返回 `{turn, call_seq}` 供断点续放；`from_recipe(steps, answer)` 把「工具调用配方」编译成脚本。**结构化 JSON 场景可直接用 `{"content": "<json 文本>"}` 脚本项驱动**（Planner/Validator 的 Mock 测试就靠这个）。

### 2.3 local_openai.py — 真实端点的全部工程（390 行，本站核心）

纯标准库 `urllib.request` 实现，零 SDK 依赖。五个关注点：

**① 重试退避**（`_post_with_retries`，:208-254）：

```python
    def _post_with_retries(self, payload: dict[str, Any]) -> dict:
        """带指数退避的 POST,返回解析后的 JSON 体。"""
        url = self._chat_url()
        data = json.dumps(payload).encode("utf-8")
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._do_post(url, data)
            except RetryableError as e:
                last_exc = e
                if attempt >= self.max_retries:
                    break
                wait = min(self.backoff_cap, self.backoff_base * (2 ** attempt))
                if e.retry_after is not None:
                    wait = max(wait, e.retry_after)
                time.sleep(wait)
            except urllib.error.HTTPError as e:
                if e.code not in _RETRYABLE_STATUS:
                    self._raise_http_error(url, e)
                …
            except urllib.error.URLError as e:
                # 连接失败/拒绝/重置视为可重试
                …
            except TimeoutError as e:
                # 读超时(thinking 模型长生成等)同样可重试;socket.timeout 是 OSError
                # 但不是 URLError,需单独捕获,否则会穿透重试循环(Layer 7 实测发现)
                …
        raise ConnectionError(
            f"多次重试后仍无法完成对本地模型服务 {url} 的请求。"
            f"请确认本地 OpenAI 兼容服务已启动且超时预算充足。原始错误: {last_exc}"
        )
```

常量：`_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}`，退避 `min(8s, 0.5s×2^attempt)`，尊重 `Retry-After` 头。**`TimeoutError` 单独捕获**的注释是 Layer 7 真实实测的战果：`socket.timeout` 是 OSError 但不是 URLError，不单独捕获会穿透重试循环——回归测试 `test_timeout_error_is_retryable` 固化。流式 `_post_sse` **不做重试**（:260 注释：「已开始发送无法安全重放」）。

**② 流式 SSE 解析**（`complete_stream`，:137-188）：

```python
        for event in self._post_sse(payload):
            choices = (event.get("choices") or [{}])
            delta = (choices[0] or {}).get("delta") or {}
            if delta.get("content"):
                acc_content += delta["content"]
            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                slot = acc_calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if tc.get("id"):
                    slot["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["arguments"] += fn["arguments"]     # arguments 字符串累加
            …
            yield ModelResponse(
                content=acc_content,
                tool_calls=self._assemble_tool_calls(acc_calls),
                finish_reason="",
                usage=dict(usage),
            )
        # 最后一次:补全 finish_reason;若服务器未返回 usage,回退启发式
        if not usage["completion_tokens"]:
            usage["completion_tokens"] = self.tokenize_len(acc_content)
```

每次 yield 是「到目前为止」的累积快照（delta 模式）；tool_calls 按 `index` 分桶、arguments 字符串累加、`_assemble_tool_calls` 按 index 排序输出；`stream_options={"include_usage": True}` 尽量要服务端回 usage（`_build_payload` :205）。

**③ 协议降级 NATIVE→TEXT_JSON**（`complete()`，:105-135）三条触发路径：

```python
        if tools and self.protocol_mode == "text_json":
            # 降级后:tools 不进 payload,工具目录注入 system 消息
            messages = [Message("system", self._text_protocol_instructions(tools)),
                        *list(messages)]
            tools_effective = None
        else:
            tools_effective = tools
        payload = self._build_payload(messages, tools_effective, temperature, stream=False, …)
        try:
            body = self._post_with_retries(payload)
        except ConnectionError:
            # 端点拒绝 tools 请求(典型 HTTP 400)→ 单向降级文本协议重试
            if tools_effective and self.protocol_mode == "native" and self.protocol_fallback:
                self.protocol_mode = "text_json"
                return self.complete(messages, tools, temperature)
            raise
        resp = self._parse(body)
        # 文本动作解析优先(原生返回无 tool_calls 时);不可解析且允许降级 → 降级重试
        if tools and not resp.tool_calls and not self._apply_text_action(resp) \
                and self.protocol_mode == "native" and self.protocol_fallback:
            self.protocol_mode = "text_json"
            return self.complete(messages, tools, temperature)
        # 截断自愈:文本回复被 max_tokens 截断 → 2×max_tokens 重试一次
        heal_base = (_max_tokens or self.max_tokens) if (
            resp.finish_reason == "length" and _allow_growth
            and self.truncation_self_heal and not resp.tool_calls) else 0
        grown = min(self.max_tokens_ceiling, heal_base * 2) if heal_base else 0
        if heal_base and grown > heal_base:
            return self.complete(messages, tools, temperature,
                                 _allow_growth=False, _max_tokens=grown)
        return resp
```

(a) 端点对 tools 请求回 400 → 降级重试；(b) 原生返回无 tool_calls 但文本能被 `parse_text_action` 解析 → **就地采纳不降级**（`_apply_text_action` 把 `{"action":"tool",...}` 填回 `resp.tool_calls`，id 固定 `call_text`）；(c) 不可解析才降级。文本协议的 system 注入（`_TEXT_PROTOCOL_INSTRUCTIONS`，:37-48）要求模型只回 `{"action": "tool", "name", "arguments"}` 或 `{"action": "final", "content"}` 纯 JSON。**截断自愈**：`finish_reason=="length"` 且无 tool_calls → `min(32768, 2×max_tokens)` 递归重试一次（`_allow_growth=False` 防无限膨胀）。协议状态机用本地 HTTPServer 桩做行为级单测（`test_local_openai_protocol.py`，6 用例），这是 miniMaster 同层覆盖率仅 32% 的测试盲区的补课。

**④ usage 启发式兜底**（`_parse`，:351-382）：completion 缺失回退 `tokenize_len(content)`；prompt 缺失保持 0（注释：无法拿到原始 prompt 文本，上层 metrics 累加时可忽略——harness 侧会用裁剪后 token 占位，双重兜底）。

**⑤ 参数纪律**：`arguments` 一律保持 JSON **字符串**格式（`_parse` :363-364 注释：「保持字符串格式(OpenAI 规范);harness 在执行工具时会自行 json.loads」；坏 JSON 原样透传，`test_models.py:78-83` 固化）。

**动手试一试**：

```bash
ollama serve & ollama pull qwen3.5:2b
python -m agentmuster run --task-file demo_task.json --config config/default.yaml --backend local_openai
```

**常见易错点**：① Ollama 模型名必须与 `ollama list` 一致；② thinking 模型会把 max_tokens 烧在思考上——配置 `max_tokens: 4096` 限幅 + 截断自愈翻倍兜底是实测教训；③ 以为流式失败会重试——不会，只有非流式可安全重放。

**练一练**：1) 写一个 3 轮 script 的任务文件（读→写→终答），跑通并核对 trajectory 里每轮的 `finish_reason`；2) 回答：`state()` 返回的 `{turn, call_seq}` 若丢失，断点恢复后 Mock 剧本会从哪一轮重放？（从头）；3) 对照 `test_local_openai_protocol.py` 的「降级」用例，说清第二个请求的 payload 与第一个的三点差异（无 tools / system 含工具目录 / 文本动作被解析）。

## 第 3 站 · 工具框架：tools/

**为什么先写它**：工具是 Agent 的手。框架先于实现——`Tool` 基类定义「能力 + 风险等级 + Schema」，安全链才能统一治理所有工具（含未来的 MCP 远端工具）。

### 3.1 base.py — Tool 基类与 Registry

```python
# 危险等级:决定 HITL 是否需要人工审批
SAFE = "safe"     # 只读,无需审批
WARN = "warn"     # 写/执行,按策略告警
HITL = "hitl"     # 高风险,必须人工审批

@dataclass
class ToolResult:
    """工具统一返回。"""
    output: str = ""
    ok: bool = True
    error: str = ""
    meta: dict = field(default_factory=dict)  # 缓存命中/文件哈希/是否脱敏等

    def to_message_content(self) -> str:
        if self.ok:
            return self.output
        return f"[工具执行失败] {self.error or self.output}"

@dataclass
class ToolContext:
    """注入到每个工具的运行期依赖。"""
    workspace: Any = None      # 沙箱工作区
    memory: Any = None         # 结构化记忆(可空)
    config: Any = None         # 全局 Config

class Tool(ABC):
    name: str = "tool"
    description: str = ""
    parameters: ClassVar[dict] = {"type": "object", "properties": {}, "required": []}
    danger: str = SAFE

    def as_openai_schema(self) -> dict:
        return {"name": self.name, "description": self.description,
                "parameters": self.parameters}

    @abstractmethod
    def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        """执行业务逻辑(参数已经过安全层校验)。"""
```

设计原则（模块 docstring）：「安全边界(参数校验/隔离/审批/去重/脱敏)在 safety 模块统一处理，**工具 execute 只做『纯业务』**，保证 安全层 与 业务层 正交。」`ToolRegistry.register` 重名抛 ValueError、`schemas()` 批量导出、`__contains__`/`__len__` 让注册表像集合一样用。

### 3.2 sandbox.py — Workspace 沙箱（五步链）

```python
    def resolve(self, path: str | Path) -> Path:
        """把用户给出的路径安全解析到工作区内部,否则抛 PathEscapeError。"""
        raw = str(path)
        if "\x00" in raw:                                  # 1. 空字节拒绝
            raise PathEscapeError("路径含空字节,已拒绝")
        # 跨平台加固:反斜杠归一为分隔符——Windows 风格的 ..\escape 在 POSIX 上
        # 同样按穿越处理,模型探测路径不因宿主平台差异而绕过安全边界
        if "\\" in raw:                                    # 2. 反斜杠归一
            raw = raw.replace("\\", "/")
        p = Path(raw)
        if p.is_absolute():                                # 3. 绝对路径默认拒绝
            if not self.allow_absolute:
                raise PathEscapeError(f"绝对路径被拒绝(工作区隔离): {path}")
            candidate = p.resolve()
        else:
            # 归一化:去掉前导 './'、正常化分隔符
            candidate = (self.root / p).resolve()          # 4. resolve 展开 .. 与 symlink
        # commonpath 校验(比 startswith 更稳,规避 /root_evil 前缀混淆)
        try:
            common = os.path.commonpath([str(self.root), str(candidate)])
        except ValueError:
            raise PathEscapeError(f"路径逃逸被拦截: {path}") from None
        if common != str(self.root):                       # 5. 双保险断言
            raise PathEscapeError(f"路径逃逸被拦截(超出工作区): {path}")
        return candidate
```

五步链每步拦什么：空字节（C 层截断攻击）、反斜杠（跨平台穿越——`..\evil` 在 POSIX 是合法文件名，不归一化就漏过）、绝对路径（`allow_absolute` 显式放开才允许）、`resolve()` 展开 `..` 与**符号链接**、`commonpath` 最终断言（`startswith` 会被 `/root_evil` 前缀混淆绕过）。

指纹与性能（`sandbox.py:89-117`）：

```python
    def snapshot(self) -> dict[str, str]:
        """返回 {相对路径: sha256},排除隐藏目录与 __pycache__。"""
        out: dict[str, str] = {}
        for f in self._iter_safe():
            try:
                out[str(f.relative_to(self.root))] = sha256_file(f)
            except OSError:
                continue
        return out

    def _iter_safe(self):
        # os.walk 自顶向下剪枝:隐藏/缓存目录在"进入前"就被剔除。
        # 不能用 root.rglob('*') 后再过滤——那会把 .conda/.mimosa 等大目录
        # 的全部条目 stat 一遍才丢弃,工作区落在项目根时 checkpoint 会慢一个数量级。
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d != "__pycache__"]
            …
```

`dirnames[:] = ...` 是 os.walk 剪枝的标准写法——**进入前**剔除隐藏/缓存目录。这是 CHANGELOG 记录的性能修复：rglob 先全量展开再过滤会让每次 checkpoint 慢一个数量级。

### 3.3 file_tools.py — 文件四件套 + grep

以 `file_edit` 为例（`file_tools.py:87-107`）——注意「唯一匹配」纪律：

```python
    def execute(self, ctx: ToolContext, path: str, old_string: str, new_string: str,
                replace_all: bool = False) -> ToolResult:
        p = ctx.workspace.resolve(path)
        if not p.exists():
            return ToolResult(ok=False, error=f"文件不存在: {path}")
        text = p.read_text(encoding="utf-8", errors="replace")
        count = text.count(old_string)
        if count == 0:
            return ToolResult(ok=False, error=f"未找到待替换字符串(长度 {len(old_string)})")
        if count > 1 and not replace_all:
            return ToolResult(
                ok=False,
                error=f"待替换串出现 {count} 次,非唯一;请加长 old_string 或设置 replace_all=true",
            )
        text = text.replace(old_string, new_string, 1) if not replace_all \
            else text.replace(old_string, new_string)
        ctx.workspace.write_text(path, text)
        return ToolResult(
            output=f"已替换 {count} 处 → {ctx.workspace.rel(p)}",
            meta={"path": ctx.workspace.rel(p), "file_hash": sha256_file(p), "replacements": count},
        )
```

为什么强制唯一：非唯一替换会改到模型没看见的位置——**让错误在工具层暴露而不是静默写坏文件**。每个工具的 meta 都带 `file_hash`，供记忆沉淀与去重层复用（docstring：「避免二次读取」）。`file_read` 输出带 `# {path} 共 N 行 (行 a..b)` 头并按 `context.max_file_content_chars` 截断；`grep_search` 每行命中截 200 字符、总输出截 8000、非法正则返回 error。

### 3.4 shell_tool.py — 受限执行

```python
    def execute(self, ctx: ToolContext, command: str, cwd: str | None = None,
                timeout: int = 10) -> ToolResult:
        workdir = ctx.workspace.resolve(cwd) if cwd else ctx.workspace.root
        if not workdir.is_dir():
            return ToolResult(ok=False, error=f"工作目录不存在: {cwd}")
        t0 = time.time()
        try:
            proc = subprocess.run(
                command, cwd=str(workdir), shell=True,
                capture_output=True, text=True, timeout=min(timeout, 30),
                errors="replace",
                env=clean_subprocess_env(),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, error=f"命令超时(>{timeout}s)被终止")
        …
        return ToolResult(
            output=out or "(无输出)",
            ok=proc.returncode == 0,
            meta={"exit_code": proc.returncode, "latency_ms": dt_ms},
        )
```

三个硬约束：工作目录锁定在工作区内（`cwd` 也过沙箱）、`timeout=min(timeout, 30)` 服务端硬上限（schema 里说默认 10s，代码兜底 30s）、`clean_subprocess_env()` 消毒环境（剥覆盖率钩子 + 强制 UTF-8）。

### 3.5 control_tools.py — 控制工具（伪工具，53 行全读）

```python
SUBMIT_RESULT = "submit_result"
REQUEST_BLOCK = "request_block"
CONTROL_TOOLS: frozenset[str] = frozenset({SUBMIT_RESULT, REQUEST_BLOCK})

class SubmitResultTool(Tool):
    name = SUBMIT_RESULT
    description = "提交当前子任务的最终结论并结束任务。summary 需含可验证证据。"
    danger = SAFE
    parameters = {
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
```

`execute()` 是占位 stub——真正语义由 harness 的前置分流实现。**不进默认注册表**（`build_registry()` 只有 7 个内置工具，`test_control_tools.py:9-13` 明确断言 `not reg.has("submit_result")`），由编排层 `_build_harness` 追加注册。`submit(success=False)` 仍是 completed 状态，失败判定由编排层看 `control` 字段——**状态归状态、结论归结论**。

### 3.6 mcp_client.py — MCP 接入（零依赖 stdio）

JSON-RPC 2.0 over stdio，协议版本 `2024-11-05`。握手（`MCPStdioClient.start`，:45-72）：

```python
    def start(self) -> list[dict[str, Any]]:
        """启动 server 并完成握手,返回远程工具描述列表。"""
        try:
            self._proc = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # server 日志走 stderr,避免撑爆管道
                text=True,
                encoding="utf-8",
                env=clean_subprocess_env(),
            )
        except OSError as exc:
            raise MCPError(f"MCP server 启动失败 ({self.command}): {exc}") from exc
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        self._request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "agentmuster", "version": "0.1.0"},
        })
        self._notify("notifications/initialized", {})
        result = self._request("tools/list", {})
        tools = result.get("tools") or []
        …
        return tools
```

Windows 兼容的关键（模块 docstring）：「读侧用后台线程 + 队列实现带超时的请求等待——**Windows 管道不支持 select**」。`_request` 用 `_send_lock` 串行化写入、按 id 匹配响应、`queue.get(timeout)` 超时抛 `MCPError`；server 崩溃（`poll()` 非 None）直接抛；`_read_loop` 遇流关闭 put 一个 `MCPError` 哨兵。

`MCPProxyTool` 零转换注册（:153-167）：

```python
    def __init__(self, client: MCPStdioClient, tool_desc: dict[str, Any]) -> None:
        self._client = client
        self._remote_name = str(tool_desc.get("name", ""))
        self.name = f"mcp_{self._remote_name}"            # 前缀防与内置工具冲突
        self.description = str(tool_desc.get("description")
                               or f"MCP 远程工具 {self._remote_name}")
        schema = tool_desc.get("inputSchema") or {"type": "object", "properties": {}}
        self.parameters = schema  # 远端 inputSchema 即 JSON Schema,零转换
        self.danger = WARN

    def execute(self, ctx, **kwargs) -> ToolResult:
        del ctx  # 远程工具由 server 治理,本地沙箱不适用
        ok, text = self._client.call_tool(self._remote_name, kwargs)
        return ToolResult(ok=ok, output=text if ok else "",
                          error="" if ok else text)
```

`attach_mcp_tools`（:170-198）的失败降级：`server_cmd` 为空返回 None；任何异常（启动失败/握手失败/工具清单为空）都 `emit("mcp_unavailable", ...)` 后返回 None——**系统降级为纯内置 7 工具继续运行，绝不抛出打断主流程**；成功则 `atexit.register(client.close)` 兜底回收进程并 `emit("mcp_connected")`。远端工具与内置工具走**同一套** SafetyGuard（`test_mcp.py:61-68` 验证远端 schema 的 required 缺参会被本地 `validate_params` 拦截）。

**动手试一试**：

```bash
python -m agentmuster run --task-file demo_task.json --hitl-policy allow --workspace ./ws
# 观察:shell_exec 被 HITL 审批(allow 策略自动放行);写 .agentmuster 后看 trajectory 里的 tool_call 状态
```

**常见易错点**：① 以为路径逃逸靠 `startswith`——是 `commonpath`；② 在 Windows 上测 `..\` 穿越期待被放过——已归一化拦截；③ 以为 MCP 工具需要单独安全策略——统一走 SafetyGuard。

**练一练**：1) 手动调 `Workspace(root="./ws").resolve("../evil")` 与 `resolve("a/../../evil")`，确认都抛 `PathEscapeError`；2) 在 Linux/WSL 下试 `resolve("..\\evil")`，验证反斜杠归一化；3) 回答：`file_edit` 的 old_string 匹配到两处且未开 replace_all 会发生什么？（报错「非唯一」，不写入）；4) 用 `tests/mcp_fake_server.py` 起一个假 MCP server，观察 `attach_mcp_tools` 成功与失败两条路径的事件。
## 第 4 站 · 安全边界：safety/

**为什么后写它（在 tools 之后）**：安全层与业务层正交——先有工具框架，安全链才有「统一的拦截点」。`safety/guard.py` 的 docstring 开宗明义：「工具 execute 不关心安全，所有调用在进入 execute 之前都必须通过 SafetyGuard 的检查链。」

### 4.1 repeat_guard.py — 三重死循环检测（118 行全读，批次②核心）

```python
"""重复动作 Guard:连续重复 + 振荡(窗口计数 / 周期循环)三重检测。

防死循环闭环的三条规则(移植自 miniMaster,快照 24f4247):
1. 连续重复:同一指纹连续出现超过 max_repeat 次;
2. 窗口计数:最近 window_size 步内同一指纹累计 >= window_max 次(绕开交替的刷步);
3. 周期检测:末尾出现步长 2~3 的 A→B→A→B 循环(振荡)。

命中任一规则即拦截,并把原因回灌给模型逼迫策略切换。在 AgentMuster 中由
SafetyGuard 检查链调用(执行前拦截);每子任务一个独立实例,指纹状态天然隔离。
"""
```

**指纹**（:44-49）：`sha256(json.dumps({"action": action, "args": args}, ensure_ascii=False, sort_keys=True))`——对工具名+全部参数做规范化 JSON 后取哈希，**参数任何变化都产生不同指纹**。**状态**（:39-42）：`_last_fingerprint` + `_consecutive` 计数器 + 两个 `deque(maxlen=window_size)`（指纹历史与动作名历史）。

**三重规则的完整 check**（:51-102）：

```python
    def check(self, action: str, args: dict) -> GuardVerdict:
        fp = self.fingerprint(action, args)
        if fp == self._last_fingerprint:
            self._consecutive += 1
        else:
            self._consecutive = 1
        self._last_fingerprint = fp
        self._history.append(fp)
        self._action_names.append(action)

        # 规则一:连续重复
        if self._consecutive > self.max_repeat:
            return GuardVerdict(
                allowed=False,
                repeat_count=self._consecutive,
                rule="consecutive",
                message=(
                    f"动作 '{action}' 与上一次完全相同,已连续重复 {self._consecutive} 次,"
                    f"超过上限 {self.max_repeat},本次调用被 Guard 拦截。"
                    "请更换策略:调整参数、换用其他工具,或用 submit_result 汇报结论。"
                ),
            )

        count = self._history.count(fp)

        # 规则二:窗口内高频复现
        if count >= self.window_max:
            return GuardVerdict(
                allowed=False,
                repeat_count=count,
                rule="window",
                message=(
                    f"动作 '{action}'(含相同参数)在最近 {self.window_size} 步内已出现 "
                    f"{count} 次,达到窗口上限 {self.window_max},疑似低效刷步,已拦截。"
                    "请总结已知信息并改用不同方法,或用 submit_result 收口。"
                ),
            )

        # 规则三:周期性振荡(A→B→A→B)
        period = self._detect_cycle()
        if period is not None:
            return GuardVerdict(
                allowed=False,
                repeat_count=period * 2,
                rule="cycle",
                message=(
                    f"检测到长度 {period} 的动作循环(同样几个调用反复交替),本次调用被 "
                    f"Guard 拦截。请跳出循环:换策略、升级汇报或 submit_result 收口。"
                ),
            )

        return GuardVerdict(allowed=True, repeat_count=self._consecutive)

    def _detect_cycle(self) -> int | None:
        hist = list(self._history)
        for p in self.cycle_periods:
            if len(hist) >= 2 * p and all(
                hist[-1 - i] == hist[-1 - p - i] for i in range(p)
            ):
                return p
        return None
```

三条规则各打击什么：连续重复打击「同一个调用无限重试」；窗口计数打击「绕开连续重复的交替刷步」（12 步窗口内同指纹 ≥4 次）；周期检测打击「A→B→A→B 乒乓」（步长 2~3 的严格振荡——`hist[-1-i] == hist[-1-p-i]` 对末尾 2p 个元素两两比对）。**三条 message 都是策略引导语**——「调整参数、换用其他工具，或用 submit_result 汇报结论」，回灌给模型。

`reset()`（:113-118）：任务切换清空全部指纹状态——「跨任务的同参数调用不算死循环」。

### 4.2 policy.py — 动作白名单（65 行全读）

```python
class Role(StrEnum):
    PLANNER = "PLANNER"
    EXECUTOR = "EXECUTOR"
    VALIDATOR = "VALIDATOR"

class Action(StrEnum):
    # Planner
    CREATE_TASKS = "create_tasks"
    REPLAN = "replan"
    # Executor 控制动作(非工具,由 AgentHarness 在工具分发前拦截处理)
    SUBMIT_RESULT = "submit_result"
    REQUEST_BLOCK = "request_block"
    # Validator
    VERIFY = "verify"

# 角色基础白名单(Executor 的工具白名单在构造时并入)
BASE_WHITELIST: dict[Role, set[str]] = {
    Role.PLANNER: {Action.CREATE_TASKS.value, Action.REPLAN.value},
    Role.EXECUTOR: {Action.SUBMIT_RESULT.value, Action.REQUEST_BLOCK.value},
    Role.VALIDATOR: {Action.VERIFY.value},
}

class ActionPolicy:
    """某个角色在当前上下文下的动作白名单 = 基础控制动作 + 附加动作。"""

    def __init__(self, role: Role, extra_actions: set[str] | None = None) -> None:
        self.role = role
        self.allowed = frozenset(BASE_WHITELIST[role] | set(extra_actions or set()))

    @classmethod
    def for_executor_with_tools(cls, tool_names: list[str]) -> ActionPolicy:
        return cls(Role.EXECUTOR, set(tool_names))

    def enforce(self, action: str) -> None:
        if not self.allows(action):
            raise PolicyViolation(
                f"角色 {self.role.value} 越权: 动作 '{action}' 不在白名单 "
                f"{sorted(self.allowed)} 内,操作已被拦截"
            )
```

模块 docstring 指明白名单有**两个执行点**：`enforce()`（角色对象内部硬校验，抛 PolicyViolation）与 `SafetyGuard.check(allowed_tools=...)`（工具执行链拦截，拒绝原因回灌）。本项目实际走第二点：编排层从 `task.extra["allow_tools"]` 取白名单 → `harness.allowed_tools = set(allow) | CONTROL_TOOLS`（控制动作恒追加）→ `guard.check` 执行。

### 4.3 redact.py — 脱敏清单（36 行全读）

```python
DEFAULT_PATTERNS: list[tuple[str, str]] = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----(.*?)-----END [A-Z ]*PRIVATE KEY-----",
     "[REDACTED_PRIVATE_KEY]"),
    (r"(?i)\bsk-[A-Za-z0-9]{16,}\b", "[REDACTED_API_KEY]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]"),
    (r"\bghp_[0-9A-Za-z]{20,}\b", "[REDACTED_GITHUB_TOKEN]"),
    (r"(?i)\b(api[_-]?key|secret|token|passwd|password)\s*([:=])\s*[^\s\"']+",
     r"\1\2 [REDACTED]"),
    (r"(?i)Bearer\s+[A-Za-z0-9._-]{6,}", "Bearer [REDACTED]"),
]

class Redactor:
    def __init__(self, patterns=None, enabled: bool = True):
        self.enabled = enabled
        self.patterns = [(re.compile(p, re.DOTALL), r) for p, r in (patterns or DEFAULT_PATTERNS)]

    def redact(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        for regex, repl in self.patterns:
            text = regex.sub(repl, text)
        return text
```

6 条正则按序替换（靠前的优先）；全部以 `re.DOTALL` 编译——**保证私钥块跨行匹配**。第 5 条的 `r"\1\2 [REDACTED]"` 用捕获组回引，保留键名只换值（`password: xxx` → `password: [REDACTED]`）。应用点四层：工具输出回灌前（`harness._run_one_tool` 末尾）、工件导出（`artifacts.py`）、JSON 落盘（`util.json_dump`）、SFT 采集（`sft_collector.py:44-45`）——纵深防御。测试覆盖 8 个绕过变体（大小写 KEY、冒号无空格、行尾、Bearer、password=、`secret :`、RSA 私钥块），断言原密文不再出现。

**常见易错点**：① 以为 Guard 拦截会抛异常——返回 `[已拦截]` 文本回灌；② 配了 `allow_tools` 却发现控制工具还能调——控制动作恒在白名单；③ 把去重和振荡 Guard 当一个东西——去重管「同参数重复」的缓存短路，Guard 管「行为模式死循环」的拦截，且缓存命中会喂给 Guard 计数。

**练一练**：1) 用 `RepeatGuard(max_repeat=2)` 连续 check 同一 action/args 三次，验证第三次 `rule="consecutive"`；2) 构造 `A→B→A→B` 序列，验证 `rule="cycle"`；3) 写一个 `CallbackProvider` 恒返回 False 的 harness，观察 shell_exec 输出与 metrics 的 `denied_actions`；4) 把含 `password=super_secret` 的文本喂给 `Redactor().redact`，核对键名保留。

## 第 5 站 · 上下文治理：context/

**为什么先写它**：上下文窗口是 Agent 最稀缺的资源；治理策略直接决定「长任务能不能跑完」与「跑完时还记不记得开头」。5.3 节已逐行精读 `assemble()` 与 `_enforce_budget`，本站补齐其余两件。

### 5.1 tokens.py — 估算器（37 行全读）

```python
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    other = len(text) - cjk
    # 分段避免单个超长 ASCII 块被 4 整除后低估;+1 保证非空文本至少 1 token
    return cjk + (other + 3) // 4
```

模块 docstring 的设计宣言：「采用『中文按字、其余按 4 字符/token』的混合启发式——无需模型分词器即可得到一个稳定、可复现的预算控制基准(评测确定性诉求)。估算只需具备单调性与稳定性，不需要与真实 tokenizer 分毫不差。」`(other + 3) // 4` 是向上取整——防超长 ASCII 块被整除后低估。

### 5.2 summarizer.py — 三档摘要器

`DeterministicSummarizer`（默认）：`[步骤 N]` + `助手结论: <截160字>` + 每条工具结果 `- 工具名: <截120字>`。`LLMSummarizer` 的三重回退已在上文引用（backend 为 None/抛异常/返回空 → 全部回退 deterministic——「保证上下文裁剪永不因摘要失败而中断」）。`NoopSummarizer`：只输出 `[步骤 N 已折叠]`——「对照实验用:折叠时直接丢弃(用于评测摘要收益)」。

### 5.3 SYSTEM_PROMPT — 一段值得背的提示词（`manager.py:23-28`）

```python
SYSTEM_PROMPT = (
    "你是 AgentMuster,一个本地编码 Agent,在给定工作区内完成代码任务。\n"
    "你通过工具调用操作文件与执行命令。所有路径必须是工作区内的相对路径。\n"
    "优先使用历史摘要与结构化记忆中的信息,避免重复读取同一文件。\n"
    "当任务完成时,直接给出简洁的最终回答,不要再发起工具调用。"
)
```

四句话对应四个机制：沙箱（相对路径）、记忆（避免重读）、循环退出条件（完成给终答）。提示词不是装饰——它是上下文组装的第一块砖，也是「优先用摘要」这条纪律与记忆系统的契约。

**练一练**：1) 塞 20 轮对话 `assemble()` 后打印 `last_prune.strategies` 与压缩率；2) 换 `noop` 摘要器再 assemble，对比历史摘要区差异；3) 回答：为什么 `_enforce_budget` 循环要设 40 字符下限？（防止单消息被缩到无意义、循环可终止）。

## 第 6 站 · 结构化记忆与检索：memory/

**为什么先写它**：上下文是「现在」的记忆，结构化记忆是「跨任务」的记忆。没有它，follow-up 任务会把父任务的工作全部重做一遍。模块 docstring 点出关键收益路径：「follow-up 任务只需要【任务摘要 + 相关文件摘要】就能继续推进，不必再打开文件重读——这正是『重复读文件 -> 0』的机制来源。」

### 6.1 store.py — 三层存储与哈希去重

文件摘要的确定性生成（`store.py:28-34`）：

```python
def summarize_file_content(content: str, max_chars: int = 600) -> tuple[str, list[str]]:
    """确定性文件摘要:头部片段 + 关键符号(函数/类/导入行),不依赖模型。"""
    lines = content.splitlines()
    head = "\n".join(lines[:8])
    summary = truncate(head, max_chars)
    symbols = [ln.strip() for ln in lines if _SYMBOL_RE.match(ln)][:20]
    return summary, symbols
```

`_SYMBOL_RE = re.compile(r"^\s*(def |class |async def |import |from )")` 抽符号——零模型成本。**核心去重**（`remember_file`，:120-157）：

```python
    def remember_file(self, path: str, content: str = "", sha256: str = "",
                      task_id: str | None = None, content_hash: str = "",
                      summary: str = "", symbols: list | None = None) -> tuple[bool, FileRecord]:
        """记录/更新文件摘要。返回 (是否真正更新, 记录)。内容哈希一致则跳过(去重关键)。"""
        digest = sha256 or content_hash or (sha256_text(content) if content else "")
        rec = self.files.get(path)
        now = now_iso()
        if rec is not None and rec.sha256 == digest and digest:
            # 内容未变:摘要仍有效,不重算、不计为一次"重读"
            rec.last_read_at = now
            if task_id and task_id not in rec.acquired_from:
                rec.acquired_from.append(task_id)
            return False, rec
        …
```

哈希一致直接 `return False, rec`——不重算摘要、不计为重读。这是「follow-up 重读归零」的底层保证；读取前 `has_fresh_summary(path, digest)` 可短路判断。

**follow-up 注入**（`followup_context`，:182-194）：

```python
    def followup_context(self, task_id: str | None = None,
                         parent_task_id: str | None = None, max_files: int = 12) -> str:
        """生成注入 follow-up 任务的记忆块(任务摘要 + 文件摘要)。"""
        blocks: list[str] = ["# 结构化记忆(来自之前的任务)"]
        pid = parent_task_id or (self.parent_of(task_id) if task_id else None)
        if pid and pid in self.tasks:
            t = self.tasks[pid]
            blocks.append(f"- 父任务 {pid}: {truncate(t.summary or t.goal, 200)}")
            for f in self.relations["task_files"].get(pid, [])[:max_files]:
                rec = self.files.get(f)
                if rec:
                    blocks.append(f"- 文件 {f}: {truncate(rec.summary, 160)}")
        return "\n".join(blocks)
```

父任务摘要截 200 + 关联文件摘要每条截 160（最多 12 个）——注入进 base 消息区，follow-up 任务无需重开文件即可推进。持久化为 tasks.json/files.json/relations.json 三文件；`load` 对 relations 做键归一化（:325-331 注释：「避免旧文件缺键导致 KeyError」）。

### 6.2 vectors.py — 三种检索模式（272 行全读）

**HashingEmbedder**（:55-96）——零依赖语义检索的精妙实现：

```python
class HashingEmbedder(EmbeddingProvider):
    """零依赖、确定性字符 n-gram 哈希嵌入器(默认)。

    把文本切成字符 n-gram,对每段做稳定哈希(MD5,避免 Python hash 随机化)落入
    dim 个桶,累加后 L2 归一化。同一文本必得同一向量(确定性),且共享字符片段的
    文本会有较高余弦相似度 —— 因此同义改写(共享汉字)也能被部分召回。
    """

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        norm_text = (text or "").lower().strip()
        grams: list[str] = []
        if self._include_unigram:
            grams += list(norm_text)                       # 单字
        grams += self._grams(norm_text, self._ngram)       # 字符 2-gram
        if not grams:
            return vec
        for g in grams:
            digest = hashlib.md5(g.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim   # MD5 前 4 字节 mod 256
            vec[idx] += 1.0
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
```

为什么用 MD5 而不是内建 `hash()`：**Python 哈希随机化**（`PYTHONHASHSEED`）会让每次进程重启后同一文本得到不同向量——MD5 保证跨进程确定性。BM25（:186-233）纯 Python 实现：k1=1.5、b=0.75、`idf = log(1 + (n - d + 0.5) / (d + 0.5))`；分词 `tokenize` 用 `[a-zA-Z0-9]+|[\u4e00-\u9fff]`——ASCII 连续串一词、汉字单字一词，中英兼容。

**HybridRetriever.rank**（:258-269）——混合检索的核心：

```python
    def rank(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        q_vec = self.embedder.embed(query)
        q_tokens = tokenize(query)
        dense = dict(self.index.search(q_vec, top_k=max(top_k, len(self.index) or 1)))
        sparse = dict(self.bm25.search(q_tokens, top_k=max(top_k, len(self.bm25.doc_ids) or 1)))
        d_n = self._normalize(dense)      # 各自按最大值归一化
        s_n = self._normalize(sparse)
        ids = set(d_n) | set(s_n)
        hybrid = {i: self.alpha * d_n.get(i, 0.0) + (1 - self.alpha) * s_n.get(i, 0.0)
                  for i in ids}
        ranked = sorted(hybrid.items(), key=lambda x: x[1], reverse=True)
        return [(i, float(s)) for i, s in ranked[:top_k]]
```

两路分数**各自按最大值归一化**后再 α 加权融合（α 默认 0.5）——量纲统一是融合的前提。Layer 5 实测（n=82）：substring recall@1/3/5 = 28%/28%/28%、MRR@5 0.44 → hybrid 61%/63%/63%、MRR@5 **0.98**。

**常见易错点**：① 手动改了工作区文件但记忆还是旧摘要——哈希不同会触发重算，这是特性；② 以为 vector 模式需要下载模型——默认 HashingEmbedder 零依赖零下载；③ `memory.enabled=false` 时 follow-up 不注入也不落盘（评测对照臂行为）。

**练一练**：1) `remember_file` 写入同一文件两次，第二次返回 `(False, rec)`；2) 构造父子任务并调 `followup_context`，核对注入块内容；3) 对同一语料分别用 substring 与 hybrid 查一条同义改写 query（对照 test_vectors.py 的断言）；4) 把 `alpha` 调成 0.0 与 1.0，观察 hybrid 退化。

## 第 7 站 · 断点与漂移：checkpoint/

**为什么先写它**：主循环是长时过程，任何一步都可能被打断。断点模块刻意做得极薄——**存储与语义分离**：`CheckpointStore` 只管「存取 JSON」，快照「存什么、何时存」全部由 harness 决定（5.4 节已逐行精读 `_checkpoint` 与 `compare`）。

`atomic_write` 的 Windows 细节（`util.py:48-71`）值得单独记：

```python
def atomic_write(path: str | Path, content: str) -> None:
    """原子写文本文件:先写临时文件再替换,避免中途崩溃留下半截文件。

    Windows 上病毒扫描或索引服务可能在刚写入后短暂占用目标文件,因此对
    PermissionError 做有界重试;其他 I/O 异常仍立即向调用方报告。
    """
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        for attempt in range(8):
            try:
                os.replace(tmp, p)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
```

`os.replace` 是原子的（同分区 rename）；PermissionError 有界重试 8 次、间隔递增；`BaseException` 分支清理临时文件——三处都是真实事故的疤痕。

**常见易错点**：① resume 不会自动「跳过已完成工作」——是步级续接（step_index 起），Mock 剧本游标靠 `backend_state` 复位；② 手改工作区文件后 resume 看到 drift 警告是特性不是 bug；③ `checkpoint.json`（聚合工件）与 `checkpoints/` 目录（断点本体）是两回事。

**练一练**：1) 跑一个任务到一半 Ctrl-C，检查 checkpoint 的 `workspace_fingerprint`；2) 在工作区加一个新文件后 `resume`，核对 DriftReport 的 `added` 列表；3) 把 `checkpoint.interval_steps` 改成 1 再跑，数 checkpoint 事件频次；4) 回答：为什么 prune 时机要「裁剪前强制落盘」？（裁剪是深拷贝重算，崩在半路也能回到裁剪前的完整现场）。
## 第 8 站 · 主循环：agent/harness.py（核心站，633 行文件导读）

**为什么压轴**：它是前面所有站的总装车间——只有认识了每个零件，主循环才一眼可读。5.1/5.2 节已逐行精读 `_run`/`resume`/`_execute_tools`/`_run_one_tool`/`_after_tool`/`_checkpoint`，本站给出**全文件的阅读地图**与尚未覆盖的组件。

### 8.1 文件结构导读（按行号）

| 行号 | 组件 | 一句话 |
| --- | --- | --- |
| 1-16 | 模块 docstring | 主循环 ASCII 图 + 设计宣言「不关心模型是否聪明，只保证确定性、可观测、可恢复」 |
| 45-69 | `_msg_to_dict` / `_turn_to_dict` 系列 | 消息/轮次 ↔ dict 序列化（checkpoint 用）；轮含可选 `user` 位 |
| 72-81 | `_metrics_restore` | 指标逐字段回填（resume 用），`compression_ratios` 列表单独恢复 |
| 84-89 | `_EMPTY_ANSWER_REMINDER` | 空终答重问的提醒文案常量 |
| 92-129 | `JsonFormatter` / `get_logger` | text/json 双格式日志；**FileHandler 前先 `mkdir(parents=True)`**（CI 全新 checkout 修复） |
| 132-161 | `AgentHarness.__init__` | 全部依赖注入；`allowed_tools` 与 `_control_signal` 是批次②新增的两个编排层注入口 |
| 165-216 | `build()` | 装配工厂（2.3 节已逐行精读） |
| 219-227 | `_emit()` | 事件出口，`contextlib.suppress(Exception)` 包裹 |
| 230-267 | `run()` / `resume()` | 都是 `_run()` 的薄封装；resume 先漂移检测再恢复四件套 |
| 270-454 | `_run()` | 主循环（5.1 节逐行精读） |
| 457-507 | `_execute_tools()` | 一轮工具调用：参数解析 → 控制分流 → 逐个 `_run_one_tool` |
| 509-538 | `_run_one_tool()` | 安全链 + 审批 + 执行 + 脱敏（5.2 节逐行精读） |
| 540-563 | `_after_tool()` | 统计 + 文件记忆自动沉淀 |
| 566-593 | `_checkpoint()` | 快照构建与落盘（5.4 节逐行精读） |
| 595-607 | `_remember_task` / `_sync_guard_metrics` | 收尾两件：任务摘要沉淀、guard 指标同步 |
| 627-633 | `_make_embedder()` | 按配置选嵌入器：`hashing`（默认零依赖）或 `fastembed`（懒加载） |

### 8.2 _execute_tools 的参数容错与事件发射

```python
    def _execute_tools(self, raw_calls: list[dict], step_index: int | None = None
                       ) -> tuple[list[ToolCall], list[Message]]:
        """执行一轮工具调用:安全链 -> 执行 -> 脱敏 -> 记忆沉淀。"""
        calls: list[ToolCall] = []
        tool_msgs: list[Message] = []
        max_calls = int(self.config.get("harness.max_tool_calls_per_turn", 8))
        ctx = ToolContext(workspace=self.workspace, memory=self.memory, config=self.config)

        for tc in raw_calls[:max_calls]:
            …  # 参数解析 + 控制分流(5.2.1 节已引)
            tool = self.registry.get(name) if self.registry.has(name) else None
            if tool is None:
                call.status = "denied"
                call.error = f"未知工具: {name}"
                output = f"[已拦截] 未知工具: {name}"     # 未知工具判 denied 而非报错
            else:
                t0 = time.time()
                output, meta = self._run_one_tool(tool, params, ctx)
                tool_latency = int((time.time() - t0) * 1000)
                call.status = meta.get("status", "ok")
                call.error = meta.get("error")
                call.output = output
                call.meta = meta
                self._emit({"type": "tool_call", "step_index": step_index,
                            "name": name, "status": call.status,
                            "latency_ms": tool_latency, "ts": now_iso()})
            calls.append(call)
            tool_msgs.append(Message("tool", output, name=name, tool_call_id=tc.get("id", "")))
        return calls, tool_msgs
```

两个细节：未知工具**判 denied 而非抛错**（模型幻觉出的工具名只是被拒绝，任务继续）；每个工具调用都发 `tool_call` 事件（含 status 与 latency）——SSE 时间线与 trace.json 的叶子 span 都靠它。

### 8.3 事件全集与「只写轨迹不发事件」的四种情况

Harness 直接 `_emit` 8 种事件：`task_start / step_start / model_call / step_end / tool_call / checkpoint / control_end / task_end`。**只写 trajectory.jsonl、不发事件**的四种：`empty_answer_nudge`、`max_steps`、`error`、`interrupt`（分别见 `harness.py:365, 419, 425, 311`）——它们是「过程细节」而非「消费方关心的里程碑」。所有 `_emit` 包 `contextlib.suppress(Exception)`——「埋点绝不拖垮主链路」。

**动手试一试**：

```bash
# 用带 script 的任务直接驱动主循环,观察每一步的事件与工件
python -m agentmuster run --task-file demo_task.json --workspace ./ws
cat .agentmuster/artifacts/demo_hello/trajectory.jsonl   # 逐行看事件序列
```

**常见易错点**：① `max_steps` 是 for 的 range 上限，每步 = 一次模型调用 + 其全部工具执行；② 在 `on_event` 回调里抛异常会被 suppress 吞掉；③ 手动构造 `TaskInput` 忘了 `extra` 传 dict——编排层的 retry_lessons 注入会静默失效。

**练一练**：1) 跑通 demo 后逐行读 trajectory.jsonl，标出每行对应 5.1 节的哪一拍；2) 把 `max_steps` 改成 1 重跑，确认 status=max_steps 且仍有 final checkpoint；3) 写一个只会返回空内容的 Mock 任务，验证 nudge 后第二条 user 消息出现、再空则 completed；4) 回答：`for-else` 的 else 何时执行？（range 耗尽且未被 break——既没终答也没控制收口）。

## 第 9 站 · 多智能体编排：prompts.py + orchestrator/ 八件套（核心站）

**为什么值得单独一站**：这是合并工程的主体，也是「确定性代码兜底 + LLM 只做决策」这一架构原则最集中的体现。闭环主循环、状态机、失败收口已在 5.5/5.6 节逐行精读；本站补齐角色提示词全文与四个辅助模块。

### 9.1 prompts.py — 角色身份层 + 输出协议层（108 行全读）

```python
PLANNER_IDENTITY = """\
你是 AgentMuster 的 Planner(规划者)。你的唯一职责是把用户目标拆解为
可独立执行、可客观验证的子任务序列,并生成整体验收清单(Completion Checklist)。

规划准则:
1. 每个子任务必须有可观测的完成标准(文件存在/命令输出正确等),拒绝"研究/考虑"类模糊任务。
2. 任务粒度适中:单个任务应在十余步工具调用内可完成。
3. 子任务之间尽量解耦,按依赖顺序编号(T1, T2, ...)。
4. 你不执行任务、不调用业务工具,只输出结构化 JSON。"""

VALIDATOR_IDENTITY = """\
你是 AgentMuster 的 Validator(验收者)。你依据证据对 Completion Checklist
逐项判定,决定整个目标是否完成。

验收准则:
1. 只认证据:执行结论里没有可验证证据的项,一律判 satisfied=false。
2. 你不做乐观推断,"应该完成了"不算完成。
3. 未满足的项必须写明缺什么(missing_requirements),供下一轮精确修复,
   而不是笼统地说"未完成"。
4. 你不执行任务、不修改清单本身,只输出结构化 JSON 判定。"""
```

身份层的每条准则都对应一个代码机制：「可观测的完成标准」→ Checklist 逐项判定；「不做乐观推断」→ 代码级双门；「不执行任务只输出 JSON」→ `structured_complete` 的严格协议。输出协议模板（`PLANNER_PROTOCOL/REPLAN_PROTOCOL/VALIDATOR_PROTOCOL`）规定 JSON schema；REPLAN_PROTOCOL 里最关键的一句：**「不要依赖已 FAILED 或 BLOCKED 的任务——其产出视为不可用；若需要它们的产出，把相应工作直接并入新任务。」**失败压缩模板：

```python
FAILURE_COMPRESS_PROMPT = """\
任务「{title}」第 {attempt} 次尝试失败。失败前的结论/错误:
{failure}

请把这次失败压缩为给下一次重试的"教训",包含两点:
1) 失败根因(一两句);2) 下次重试应改用什么策略、应避免什么。
不超过 250 字,只输出教训文本本身。"""
```

三段式组装器（`role_system_message`，:86-108）：

```python
def role_system_message(role: str, context: dict | None = None) -> str:
    """组装角色 system 消息:身份层 + 动态上下文层 + 输出协议层。"""
    ctx = context or {}
    if role == "planner":
        sections = [PLANNER_IDENTITY]
        if ctx.get("goal"):
            sections.append(f"## 用户目标\n{ctx['goal']}")
        if ctx.get("planner_view"):
            sections.append(f"## 当前任务状态\n{ctx['planner_view']}")
        if ctx.get("missing_feedback"):
            feedback = "\n".join(f"- {m}" for m in ctx["missing_feedback"])
            sections.append(f"## 上轮验收缺失项(精确回流,本轮必须针对性解决)\n{feedback}")
        sections.append(REPLAN_PROTOCOL if ctx.get("replan") else PLANNER_PROTOCOL)
        return "\n\n".join(sections)
    …
```

**缺失项精确回流的完整链路**到此闭环：Validator 判定 → `missing_requirements` → Orchestrator 追加 BLOCKED/FAILED 注记 → `role_system_message` 渲染为「## 上轮验收缺失项(精确回流，本轮必须针对性解决)」→ Planner 增量产出 → 下一轮只跑 PENDING。

### 9.2 structured.py — 反馈重试环（41 行全读）

```python
def structured_complete(backend: ModelBackend, messages: list[Message],
                        temperature: float = 0.0, max_attempts: int = 3) -> dict:
    """发起一次结构化调用,返回解析后的 dict;失败抛 StructuredOutputError。"""
    convo = list(messages)
    last_error = ""
    for _ in range(max_attempts):
        resp = backend.complete(convo, tools=None, temperature=temperature)
        content = resp.content or ""
        if resp.finish_reason == "length":
            feedback = "你的输出被 max_tokens 截断。请精简内容,重新只输出一个完整 JSON 对象。"
        else:
            try:
                data = extract_json(content)
                if isinstance(data, dict):
                    return data
                raise ValueError("顶层不是 JSON 对象")
            except ValueError as exc:
                feedback = (f"输出不是合法 JSON({exc})。"
                            "请重新只输出一个完整 JSON 对象,不要附加任何其他文字。")
        last_error = feedback
        convo.append(Message("assistant", content))
        convo.append(Message("user", feedback))
    raise StructuredOutputError(f"结构化输出在 {max_attempts} 次尝试后仍失败: {last_error}")
```

核心容错思想：**错误反馈回灌**——每次失败把 (assistant 原文， user 反馈) 追加进会话再重试，让模型「看到自己错在哪」。两类反馈：截断反馈（finish_reason=length）与解析反馈（extract_json 逐级候选全失败）。Planner/Validator/失败压缩全部经此函数调用模型——「后端无关」：MockBackend 用 `{"content": "<json>"}` 脚本驱动，LocalOpenAI 走真实模型。

### 9.3 planner.py — 语义级重问与增量重规划

```python
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
        …
```

两层防御：结构化输出的**语法级**重试（structured_complete）+ 「tasks 为空」的**语义级**重问（JSON 合法但没有可执行任务）；checklist 缺失时从 done_criteria 兜底派生——「避免验收永假死局」（空清单 `is_complete=False`，没有兜底就永远过不了）。

`replan`（:70-95）的三个细节：空反馈直接返回 `[]`；上下文带 `planner_view`（全任务 render）+ **前 8 条缺失反馈** + 最近 8 条活动日志；`_parse_tasks(..., start_index=len(tasks))` 使缺省 id 自动续号 T{n+1}，**复用已有 id 的增量任务直接丢弃**（`new_tasks = [t for t in new_tasks if t.id not in known]`）。

### 9.4 validator.py — 判定写回与确定性补齐

```python
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
        …
```

两个「不信任 LLM」的补丁：`apply_verdict` 对**未知 item_id 直接忽略**（防幻觉编号，`checklist.py:26-32`）；清单仍有 unmet 项时**确定性补齐** missing（去重后追加「Checklist 未满足： …」）——LLM 漏报的缺失项由代码兜住。最终判定是代码级双门。

`apply_verdict` 与 `is_complete`（`checklist.py:24-39`）：

```python
    def apply_verdict(self, updates: list[dict]) -> None:
        """应用 Validator 的逐项判定:[{item_id, satisfied, evidence}]。"""
        by_id = {i.item_id: i for i in self.items}
        for upd in updates:
            item = by_id.get(str(upd.get("item_id")))
            if item is None:
                continue                     # 未知 item_id 直接忽略(防幻觉)
            item.satisfied = bool(upd.get("satisfied"))
            item.evidence = str(upd.get("evidence", ""))[:500]

    def unmet(self) -> list[ChecklistItem]:
        return [i for i in self.items if not i.satisfied]

    @property
    def is_complete(self) -> bool:
        return bool(self.items) and all(i.satisfied for i in self.items)
```

**空清单 `is_complete=False`**——避免「无清单即通过」的假阳性（`test_checklist.py:42-43` 固化）。`render()` 三态渲染 `[x]/[ ]/[?]`（None=尚未验收）。

### 9.5 working_memory.py 与 retry_archive.py — 编排层的薄记忆

```python
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
```

模块 docstring 的分工宣言：「子任务内部的执行轨迹由各 AgentHarness 的上下文治理与结构化记忆负责，**不再进入编排层**；本模块只保留两个角色视图的渲染与一个任务级活动日志。」`deque(maxlen=50)` FIFO 自动挤掉最老记录 + `threading.Lock` 并发安全 + 单条 detail 截 2000——测试验证 8 线程 ×100 条并发写后长度恰为 maxlen。

RetryArchive（`retry_archive.py:38-67`）：

```python
    def archive(self, task: Task, failure_reason: str) -> RetryRecord:
        """压缩并归档一次失败轨迹。"""
        attempt = task.attempts
        lessons = (self.compress_fn(task.title, attempt, failure_reason)
                   if self.compress_fn is not None else truncate(failure_reason, 2000))
        record = RetryRecord(
            task_id=task.id, title=task.title, attempt=attempt,
            failure_reason=truncate(failure_reason, 1500),
            lessons=truncate(lessons, 2500),
        )
        self._records.setdefault(task.id, []).append(record)   # 按任务分桶 append 不覆盖
        return record
    …
    def render_for_task(self, task_id: str) -> str:
        records = self.for_task(task_id)
        if not records:
            return ""
        lines = ["== Retry Archive:本任务的历史失败记录(务必避免重蹈覆辙)=="]
        lines += [f"- {r.render()}" for r in records]
        return "\n".join(lines)
```

三级限幅（failure_reason 截 1500、lessons 截 2500、单次压缩 prompt 内 failure 截 3000）+ 分桶追加（多次失败累积成「学费清单」）。`compress_fn` 由编排层注入 `self._compress_failure`：`context.summarizer=llm` 时用 validator 后端 + `FAILURE_COMPRESS_PROMPT` 压缩（温度 0.1），**任何异常回退 `truncate(failure, 2000)`**（`agent/orchestrator.py:127-138`）。

**常见易错点**：① `max_retries=2` 是 1 次初始 + 2 次重试共 3 次；② deterministic 模式 `_auto_verdict` 只看状态不看内容（已知边界，附录 B 第 8 条）；③ 旧式 `Callable[[str], list[dict]]` planner 会被 `_LegacyPlannerAdapter` 适配（replan 恒空、checklist 从任务派生）。

**练一练**：1) 跑 `orchestrate --goal "写两个文件 a.txt 与 b.txt" --planner llm`，对照 orchestration.json 数子任务数/轮数/checklist 项数；2) 读 `tests/orchestrator/test_loop.py` 的 S2，解释 replan 新增任务 id 为什么续号不重排；3) 把 `max_total_tokens` 调到极小复跑，找 `budget_exceeded` 事件并确认 PENDING 全转 BLOCKED；4) 回答：为什么 `from_dict` 恢复要绕过状态机校验？（快照状态是历史事实，恢复要求原样重建）；5) 复现「Validator 输出缺一个 item_id」，确认 `apply_verdict` 忽略未知编号且该项保持 unsatisfied。
## 第 10 站 · 可观测性与 API：observability/ + api/

**为什么放一起**：它们是同一条「事件总线」的两个消费者视角——Tracer 把事件重建成 span 树落盘，API 把事件实时推给浏览器。两者都对 harness **零侵入**。

### 10.1 tracing.py — 事件驱动的零侵入 Tracer（250 行）

模块 docstring 的设计宣言：「零依赖…OTLP 风格…可选桥接…**事件驱动：harness 主循环在 run/step/model/tool/checkpoint 处抛出语义事件，Tracer 仅作为事件消费者重建 span 生命周期——对 harness 零侵入。**」埋点协议注释列出 6 种事件（task_start/step_start/model_call/tool_call/checkpoint/task_end）。

`handle()` 的事件分发（`tracing.py:127-147`）：

```python
    def handle(self, event: dict) -> None:
        if not self.enabled or not isinstance(event, dict):
            return
        etype = event.get("type")
        try:
            if etype == "task_start":
                self._on_task_start(event)
            elif etype == "step_start":
                self._on_step_start(event)
            elif etype == "model_call":
                self._on_leaf_span("model_call", event, parent_id=self._step_span_id)
            elif etype == "tool_call":
                self._on_leaf_span("tool:" + str(event.get("name", "?")),
                                   event, parent_id=self._step_span_id)
            elif etype == "checkpoint":
                self._on_leaf_span("checkpoint:" + str(event.get("reason", "")),
                                   event, parent_id=self._run_span_id)
            elif etype == "task_end":
                self._on_task_end(event)
        except Exception:  # 埋点绝不能拖垮主链路
            pass
```

叶子 span 的即开即关（`_on_leaf_span`，:170-178）——**用 latency_ms 反推起点**：

```python
    def _on_leaf_span(self, name: str, event: dict, parent_id: str | None) -> None:
        latency = float(event.get("latency_ms", 0) or 0)
        now_ns = time.time_ns()
        span = self._start_span(name, parent_id=parent_id,
                                start_ns=now_ns - int(latency * 1_000_000),
                                end_ns=now_ns,
                                attributes={k: v for k, v in event.items()
                                            if k not in ("type",)})
        self._end_span(span.span_id, status=event.get("status", "ok"))
```

事件到达时调用已经结束，只能拿「当时的事件 + 延迟」——起点由 `now - latency` 反推。span 树结构：`run`（task_start 开根）→ `step:{index}`（step_start 开、下一个 step_start 或 task_end 收）→ `model_call` / `tool:{name}` 叶子。OTel 桥接（`_try_otel` + `_start_span` 内镜像）：探测 `opentelemetry-api`，可用则 `start_span` 镜像、父 context 经 `_otel_ctx` 传递，所有桥接代码 `try/except: pass`——**缺失则静默降级，零依赖导出不受影响**。导出（`export()`，:238-250）：`{artifacts_root}/{task_id}/trace.json`，顶层 `{trace_id, service, task_id, span_count, spans}`，字段与 OTel span 对齐（「便于日后接入真正的 OTLP 收集器」）。

### 10.2 fastapi_server.py — 双后端决策与任务注册表

`_RUNS` 内存注册表（:34）：`{task_id: {status, result, error, events, backend, arm, compare_group}}`。`_launch` 公共提交通道（:114-125）：

```python
    def _launch(task_data: dict, *, arm: str | None = None,
                compare_group: str | None = None) -> dict:
        """公共提交通道:/api/run 与 /api/compare 都经由这里入队。"""
        task_id = task_data.get("task_id") or ("api-" + uuid.uuid4().hex[:8])
        _RUNS[task_id] = {"status": "running", "result": None, "error": None,
                          "events": [], "backend": None,
                          "arm": arm, "compare_group": compare_group}
        bus.register(task_id)
        t = threading.Thread(target=_worker, args=(task_id, task_data, config, bus),
                             daemon=True)
        t.start()
        return {"task_id": task_id, "status": "submitted"}
```

`_worker` 的四个刻意决策（5.7.2 节已全引）：`observability.enabled=False`（SSE 已是实时追踪，不写 trace.json 免得目录脏）、`event.setdefault("task_id", ...)` 补全（harness 部分事件不带 task_id）、`backend` 尽早回填（列表立即可见）、`finally: bus.done(task_id)`（哨兵必达）。

**双 API 实现对照**：

| 维度 | stdlib（server.py，179 行） | fastapi（229 行） |
| --- | --- | --- |
| 基座 | `ThreadingHTTPServer` | FastAPI + uvicorn |
| 执行模型 | 同步阻塞：`POST /run` 跑完才返回 | 异步提交：立即返回 task_id |
| 实时事件 | 无 SSE；`/api/runs` 是「伪列表」（扫工件目录、恒 completed） | SSE 实时流；`/api/runs` 读 `_RUNS` 真注册表 |
| 独有端点 | 遗留接口 /run、/tasks、/memory | /api/compare 双跑对照、/docs |
| /health 字段 | `budget_tokens` | `hard_limit_tokens` |

为什么保留两套：核心承诺「零依赖、全离线」——stdlib 保证裸 Python 环境能起 API（fastapi 测试在依赖缺失时整体 skipif 跳过）；SSE 需要异步事件循环，作为可选增强放在 fastapi 侧。`serve --impl stdlib|fastapi` 切换，默认 stdlib。

### 10.3 monitor_page.py — 零构建监控页

单个 Python 模块：`_MONITOR_PAGE` 是内嵌 HTML 大字符串（含全部 CSS/JS/template），`VUE_RUNTIME` 指向 `static/vue.global.prod.js`（166KB vendored Vue 3 global build）。零构建策略 = 无 npm、无打包器，原生 `<script src="/vue.global.prod.js">` 加载。前端消费 SSE（`monitor_page.py` 内的 JS）：

```javascript
function watchTask(tid) {
  // 关闭旧 EventSource,新建到 /api/run/{tid}/events;
  // onmessage 逐条 JSON.parse 后 append;
  // 监听具名 done 事件 → 关流 → 置状态"完成" → pollTask 拉终态;
  // onerror → 关流并降级为单次 pollTask 轮询(兼容 stdlib 实现,那里没有 SSE)
}
```

五个区块：提交面板（后端选择/脚本 JSON/父任务 ID）、任务列表（2 秒轮询、arm 徽章「mock 臂 / ollama 臂」）、指标卡片（status/steps/tool_calls/prompt_tokens/cost_usd）、双跑对比表（两臂六行指标）、事件时间线（按 `event-{type}` 着色 + model_call/tool_call/checkpoint 专门格式化）。

**动手试一试**：

```bash
python -m agentmuster serve --impl fastapi --config config/default.yaml --port 8910
# 浏览器打开 http://127.0.0.1:8910/ → 提交任务 → 看事件时间线逐条滚动 → 点「双跑对比」
curl -N http://127.0.0.1:8910/api/run/<task_id>/events   # 抓 SSE 原始流看心跳与哨兵
```

**常见易错点**：① stdlib 模式任务列表基本不可用（伪列表），监控靠单任务轮询兜底；② API 运行目录没有 trace.json 不是 bug（刻意关闭）；③ `/api/compare` 带 script 时只 mock 臂回放剧本、ollama 臂忽略。

**练一练**：1) 分别用 stdlib 与 fastapi 起服务，diff `/health` 响应；2) 抓 SSE 流，标出心跳行、数据行与 done 事件；3) 打开 trace.json 还原 `run → step → model_call/tool_call` 父子树；4) 回答：为什么 `_worker` 在配置副本上关 observability？（SSE 已是实时追踪，避免两套可观测性产物混淆）。

## 第 11 站 · 评测体系：eval/ + benchmarks/

**为什么压轴**：评测是这个项目「自证清白」的方式，也是它与「能跑起来就行」的 demo 项目的本质差距。5.8 节已给出七层总表与三种对照；本站深入每层的判定代码。

### 11.1 runner.py — Layer 2 的三臂与信息保留探针

Layer 2 上下文治理评测（`runner.py:326-404` 节选）——治理臂/基线臂/贴边臂的变量固定：

```python
            wdg = self.output_dir / "workspaces" / (t["task_id"] + "_governed")
            rg, hg = self._run(t, wdg, budget=budget, keep_turns=keep)      # 治理臂
            wdb = self.output_dir / "workspaces" / (t["task_id"] + "_baseline")
            rb, _ = self._run(t, wdb, budget=10_000_000, keep_turns=1000)   # 不治理基线臂
            gov_total = sum(s.prompt_tokens for s in rg.steps)
            base_total = sum(s.prompt_tokens for s in rb.steps)
            ratio = (1 - gov_total / base_total) if base_total else 0.0
            hard = budget * 1.5
            within_hard = sum(1 for s in rg.steps if s.prompt_tokens <= hard)
            compliance = (within_hard / len(rg.steps)) if rg.steps else 1.0
```

信息保留探针：`expect.probe_contains` 列出的关键字符串**写入生成文件头部**，折叠截断后仍出现在 `harness.context.assemble()` 的 blob 里才算保留——「压缩率」与「信息保留率」必须同时考核，只考前者会诱导把上下文删光。贴边测试再跑 `budget=600, keep_turns=2` 验证硬限额兜底截断。

Layer 3 记忆评测的场景注入（`runner.py:421-431` 节选）：stale 场景在 follow-up 运行前改写文件（`scenario_mutate`）；missing 直接 `shutil.rmtree(wd/"memory")`；wrong_hit 用 `StructuredMemory.remember_file` **播种干扰摘要**——考「记忆会不会被错误利用」而不只是「记没记」。四场景分判：fresh 重读=0、stale 重读且读到新内容且哈希刷新、missing 优雅重读、wrong 不误用诱饵。

Layer 4 漂移矩阵（`runner.py:494-525` 节选注释）：

```python
        # whitespace/reformat 属"语义不变内容变",哈希精确比对必然检出(误报),
        # "宁可误报不可漏报",矩阵中显式测之
```

五类漂移：content_change（篡改+新增+删除）、whitespace_only（每行尾加两空格）、reformat（四空格缩进）、large_scale（300 个 bulk 文件）× 9 个停点 = 45 场景；每场景断言 `interrupted → 检出=期望`、恢复后 completed、内容正确、large_scale 恢复耗时 ≤10s。

Layer 5 检索评测的四类分判（`runner.py:655-690`）：exact 要求 `substring@3>0 且 hybrid@3≥substring@3`（证明 substring 本身可用）；synonym 要求 `hybrid@3 > substring@3`（语义增益）；distractor/empty 要求 avoid 集不进 hybrid top-3 且 `substring@3==0`；整体 ok 还要求 `avg_hybrid@3 > avg_substring@3` 且 `mrr_hybrid > 0`。

### 11.2 raw_baseline.py — 三臂的刻意差异

naive_loop 臂的「刻意不复用」清单（`raw_baseline.py:42-45` 注释）：

```python
# naive_loop(朴素 agent 循环):最简 tool-calling 循环——模型↔工具往返直到无
# tool_calls(completed)或 max_steps 耗尽。刻意不复用 harness 的上下文治理/
# 结构化记忆/checkpoint/安全审批链/去重/工件系统;只保留 Workspace 文件边界
# 与 5 个文件类工具。shell_exec(高风险审批)与 memory_query(依赖记忆系统)刻意不暴露。
_NAIVE_TOOLS: tuple[str, ...] = ("file_read", "file_write", "file_edit",
                                 "file_list", "grep_search")
```

single_shot 臂的确定性提取器：`_SINGLE_SHOT_SYSTEM` 要求模型只输出 ```` ```lang path=xxx ```` 代码块；`_FENCE_RE` 正则抽取、`_parse_block_path` 优先 `path=` 关键字、`_write_code_blocks` 写入 Workspace——**缺失交给硬断言判失败，不猜测**。工程细节：`run_suite` 对 `real/real_baseline` 不整体 `_reset` 输出目录——Layer 6 与 6b 报告共存，三臂对照才成立（专门回归测试 `test_real_baseline_suite_does_not_wipe_output_dir` 固化）。

### 11.3 layer7_multiagent.py — 客观检查器与消融

客观检查器的「不信任」哲学——每个检查器验证**运行产物**而非 Agent 自述：

```python
def check_calc(ws_root: Path, report: dict) -> tuple[bool, str]:
    rc, out = run_python(ws_root, "-c",
                         "from calc import add, sub, mul, div; "
                         "assert add(2,3)==5 and sub(5,2)==3 "
                         "and mul(3,4)==12 and div(9,3)==3")
    if rc != 0:
        return False, f"calc 函数断言失败: {out[-300:]}"
    return True, "calc 四则函数子进程断言通过"
```

`check_dep_chain` 最能体现「检查器做数据流追踪」：解析 data.json 后**动态计算** `expected_total = sum(score)`，要求它同时出现在 summary.txt 与 read_data.py 运行输出中。`check_grep` 要求 todos.txt 集合**恰好等于**预期（多列少列都失败）；`check_fizzbuzz` 断言 100 行且第 15 行是 FizzBuzz（边界值）。

消融开关的映射（`layer7_multiagent.py:216-234`）：

```python
    for item in filter(None, ablate.split(",")):
        if item == "guard":
            overrides.update(**{
                "safety.repeat_guard.max_repeat": 10**6,
                "safety.repeat_guard.window_size": 10**6,
                "safety.repeat_guard.window_max": 10**6,
            })
        elif item == "retry":
            overrides["orchestrator.max_retries"] = 0
        elif item == "budget":
            overrides["orchestrator.max_total_tokens"] = 0
        elif item == "validator":
            overrides["orchestrator.planner_mode"] = "deterministic"  # 退化为无验收闭环
```

「消融」的实现方式是**把机制放宽到永不触发**（Guard 阈值全改 10^6、重试归零、预算归零=不限、Validator 退化 deterministic）——未知消融项直接 `SystemExit`。结果聚合：`success = agent_success AND check_ok`（双布尔分离记录），指标含 rounds/attempts/tokens/retries/replans/denied_actions/duration_s；**进程退出码 = 全部 success 才 0**（第 366 行）。真实模型手动跑（不进 CI）；首测 quick 套件 3/4。

### 11.4 judge.py — LLM-as-judge 的诚实边界（82 行）

```python
    def judge(self, goal: str, file_snapshot: dict[str, str], rubric: str = "") -> JudgeVerdict:
        snapshot = "\n\n".join(
            f"### {path}\n```text\n{text}\n```" for path, text in sorted(file_snapshot.items())
        ) or "(工作区没有可读取文件)"
        prompt = (
            "你是严格、客观的代码评审员。请根据任务目标、工作区文件和评分标准判断实现是否完成。\n"
            "只输出一个 JSON 对象,不要 Markdown,格式为 "
            '{"pass":true或false,"score":0到5,"reasoning":"简短理由"}。\n\n'
            f"任务目标:\n{goal}\n\n评分标准:\n{rubric or '功能正确、边界处理合理、代码可维护。'}\n\n"
            f"工作区快照:\n{snapshot}"
        )
```

解析失败的诚实处理（`_parse`，:56-82）：先整体 `json.loads`，失败则正则 `\{.*\}`（DOTALL）抓取再试；仍失败返回 `JudgeVerdict(passed=False, score=0.0, parse_ok=False)`——**解析失败即判负，诚实不掩饰**（`test_judge_parse_failure_is_honest` 固化）。在 Layer 6 中：最终通过 = `completed AND assertions_ok AND judge.passed`（`real.py:112`）——评委是叠加在硬断言之上的**否决项**，不是替代品。已知局限：单次调用无投票、只见工作区快照不见执行过程、2b 评委实测 0/4 不可靠——结果如实保留在报告。

### 11.5 benchmark.py + generators.py — 冻结基准

`SEED = 20260819` 参数化生成五层数据后**冻结落盘入库**（`generators.py` docstring：「生成结果冻结落盘提交入库：既保留『改 seed 即可再生成一批』的参数化能力，又保证评测数据可审查、可 diff、可复现」）。任务格式（真实负例样例）：

```json
{"task_id": "t13n_read_missing_file", "layer": "regression", "kind": "negative",
 "goal": "读取不存在的 ghost.txt(应报错且优雅降级,不崩溃)。",
 "script": [{"tool_calls": [{"name": "file_read", "arguments": {"path": "ghost.txt"}}]},
            {"content": "ghost.txt 不存在,已向用户报告该错误。"}],
 "expect": {"should_fail_call": "file_read"}}
```

检索查询四类型（真实样例）：

```json
{"q": "包含 token 校验与会话管理", "relevant": ["a01"], "type": "exact"}
{"q": "登入流程的会话校验", "relevant": ["a01"], "type": "synonym"}
{"q": "如何注销账号并永久删除全部个人数据", "relevant": [], "avoid": ["a02", "a15"], "type": "distractor"}
{"q": "量子计算原理与量子门电路", "relevant": [], "avoid": ["a03", "a26"], "type": "empty"}
```

运行期可复现性三件套：Mock 回放 + 临时隔离 workdir + `test_deterministic_repeat`（context 套件连跑两次逐项相等）。`eval_history.jsonl` 追加历史供跨次退化对比。

**动手试一试**：

```bash
python -m agentmuster eval --suite all --output .agentmuster/eval      # Layer 1-5 离线
python -m agentmuster eval --suite retrieval --output .agentmuster/eval  # 只跑检索层
python -m agentmuster.eval.layer7_multiagent --suite quick --backend mock   # 冒烟(验证评测机本身)
```

**常见易错点**：① mock 下跑 real 套件会优雅 skip（报告说明需 local_openai）；② 两套「Layer 7」编号复用（嵌入器对照 vs 多智能体基准，附录 B 第 4 条）；③ Layer 7 设计上手动跑，不进 CI。

**练一练**：1) 跑 `eval --suite context`，在 report.md 找治理臂 vs 基线臂 token 对比与信息保留率；2) 读 `test_memory_regression_sensitivity`，解释「故意注入退化必须显著下跌」为什么是回归锚；3) 阅读 `check_dep_chain`，说明检查器如何动态计算期望值从而不信任 Agent 自述。

## 第 12 站 · 数据飞轮支线：sft_collector.py + kb_lora/

**为什么单独一站**：它回答「Agent 系统跑起来之后，数据资产怎么沉淀、怎么反哺模型」——Agent 应用岗位 increasingly 关心的问题。

### 12.1 sft_collector.py — 样本采集（73 行全读）

模块 docstring 点出痛点：「当前 trajectory.jsonl 只记录『agentic 骨架』(task_id / 每步 assistant 推理 / 工具调用元信息 / token)，**不含原始指令文本、不含检索上下文、不含最终答案**，因此无法直接当作 SFT 样本。」

```python
def write_sft_sample(task_dir: Path, *, task_id: str, instruction: str,
                      output: str, context: str | None = None,
                      status: str = "completed", redactor=None) -> str | None:
    """向 {task_dir}/sft_samples.jsonl 追加一条 SFT 样本。…"""
    instruction = (instruction or "").strip()
    output = (output or "").strip()
    if not instruction or not output:
        return None

    sample = {
        "task_id": task_id,
        "status": status,
        "instruction": instruction,
        "output": output,
        "context": (context or "").strip(),
        "ts": now_iso(),
    }
    text = json.dumps(sample, ensure_ascii=False, default=str)
    if redactor is not None:
        text = redactor.redact(text)          # 写前整段脱敏(复用 safety 能力)

    p = ensure_dir(task_dir) / "sft_samples.jsonl"
    with open(p, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    return str(p)
```

触发点在 harness 收尾（5.1 节已引）：`status == "completed" and config.get("artifacts.sft_log", False)`——只采成功任务、默认关闭、与轨迹解耦（「绝不破坏既有行为」）。`finalize_index()` 用 rglob 汇总所有样本文件，返回 `{total, by_status}` 轻量索引供训练前估规模。`context` 参数当前传 None——注释预留「企业知识库场景可注入 KB 上下文」。

### 12.2 kb_lora/ — 企业知识库 LoRA 微调线

与零依赖核心完全解耦（自带 requirements，需自备 torch 环境），三段式：

1. **build_kb_dataset.py（造数据）**：企业文档 1200 字符滑窗（重叠 200）切块；`--mode offline` 模板抽句改写问答（零成本冷启动）/ `--mode teacher` 调本地端点出题（失败自动回退 offline）；产出与 sft_samples.jsonl 同构的 instruction/output/context。
2. **export_sft.py（清洗导出）**：扫描工件根的 sft_samples.jsonl 与 trajectory.jsonl；清洗规则——只留 completed、instruction 5-4000 字、output 10-6000 字、按 `(instr|||output|||ctx)` 的 SHA1 去重、正则脱敏；三种模式 `kb`（context 进 system，练「带检索资料作答」）/`plain`/`agent`（轨迹 step 转多轮 tool_calls 对话）；输出 ChatML + Alpaca 双格式。
3. **train_lora.py（QLoRA 训练）**：面向 RTX 4060 8GB——Qwen3.5-2B 基座、4-bit NF4 + 双量化 + bf16、LoRA r=16/α=32/dropout 0.05 挂全部 7 个投影层、batch 2 × grad-accum 8、seq 2048、paged_adamw_8bit + 梯度检查点；TRL SFTTrainer 产出适配器。

**闭环**：harness 跑任务 → sft_collector/trajectory 产数据 → kb_lora 清洗微调 → 适配器合并进 Ollama → 经 `model.local_openai` 接回 AgentMuster 验证。面试讲「数据飞轮」的完整素材。

**常见易错点**：① 在 kb_lora 里找主项目的 import——没有，支线刻意零耦合；② 以为 sft_log 开了就采集失败任务——只采 completed；③ Ollama 推理标签 `qwen3.5:2b` 与 HF 训练 id `Qwen/Qwen3.5-2B-Instruct` 是两回事。

**练一练**：1) 开启 `artifacts.sft_log: true` 跑一个会成功的 Mock 任务，检查 sft_samples.jsonl；2) 读 `export_sft.py` 的清洗规则，说明「只留 completed + 长度门槛 + SHA1 去重」分别防什么脏数据；3) 画出数据飞轮闭环图并标注每一步的产物文件名。
***

# 第七部分：使用方式实操

## 7.1 环境准备

```bash
# 方式一:pip(推荐,核心仅依赖 PyYAML)
python -m pip install -e .

# 方式二:Conda 一键重建完整环境(dev+api+vector 全量;仓库推荐,环境落在项目内 .conda/)
conda env create -p .conda -f environment.yml

# 方式三:Docker(内置 Ollama,首次启动自动拉取 qwen3.5:2b)
docker compose up -d
```

按需安装可选依赖组：`agentmuster-harness[api]`（FastAPI+SSE+监控页）、`[vector]`（fastembed/bge-small 真实语义嵌入）、`[otel]`（OpenTelemetry 桥接）、`[dev]`（ruff+mypy+pytest）。

**验证环境**：`python -m agentmuster doctor`——输出 Python 版本、yaml/pytest 可用性、模型后端、工作区根、上下文硬上限、API 地址。

## 7.2 CLI 速查（8 个子命令）

| 命令 | 作用 | 关键参数与行为 |
| --- | --- | --- |
| `run` | 运行一个任务 | `--task-file`（必选）；任务含 `script` 强制 Mock；`--backend` 临时切换；`--hitl-policy prompt\|allow\|deny`；非 completed 退出码 1 |
| `resume` | 从断点恢复 | `--task-id`；恢复前自动漂移检测并打印报告 |
| `serve` | 启动 localhost HTTP API | `--impl stdlib\|fastapi`（默认 stdlib 零依赖）；默认 127.0.0.1:8910 |
| `orchestrate` | 多轮编排 | `--goal`（必选）、`--planner llm` 启用 LLM 角色闭环（默认 deterministic 退化）、`--max-workers` |
| `eval` | 运行评测 | `--suite all\|regression\|context\|memory\|resume\|retrieval\|real\|real_baseline\|embedder` |
| `benchmark` | 列出内置任务 | `--benchmarks` 指定数据文件 |
| `artifacts` | 查看任务工件 | `--task-id`；列出文件与大小 |
| `doctor` | 环境诊断 | 检查依赖/配置生效值 |

任务文件两种形态：`.json`（结构化，含 goal/script/setup_files/expect）与 `.md`（YAML frontmatter + 正文作 goal）。最小可跑示例见 README「快速开始」。

## 7.3 Web API 速查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/run` | 提交任务立即返回 task_id；可选 `backend` 字段按请求选后端 |
| POST | `/api/compare` | 一键双跑对照（mock+local_openai 两臂，共享 compare_group） |
| GET | `/api/run/{id}` | 轮询状态（含 backend/arm/compare_group 元数据） |
| GET | `/api/run/{id}/events` | SSE 实时事件流（done 哨兵 + 15s 心跳） |
| GET | `/api/runs` | 任务列表与事件计数 |
| GET | `/api/artifacts/{id}/{name}` | 下载工件 |
| GET | `/health`、`/` | 健康检查 + Vue 3 监控页 |

后端解析优先级：**带 script 锁 mock > 请求显式 backend > 配置默认**（`_decide_backend` 源码见 5.7.3 节）。

## 7.4 配置速查（高频项）

| 分组 | 关键项 | 默认值与说明 |
| --- | --- | --- |
| 工作区 | `workspace.root` / `allow_absolute` | 沙箱边界；默认禁止绝对路径 |
| 模型 | `model.backend` / `model.local_openai.*` / `model.pricing` | mock（离线确定性）\| local_openai；base_url 11434/v1、max_tokens 4096 限幅、retry 退避、protocol_fallback、truncation_self_heal、max_tokens_ceiling 32768 |
| 主循环 | `harness.max_steps` / `max_tool_calls_per_turn` / `empty_answer_nudges` | 30 / 8 / 1（0 关闭） |
| 上下文 | `context.hard_limit_tokens` / `keep_last_turns` / `max_file_content_chars` / `summarizer` | 6000 / 6 / 8000 / deterministic |
| 记忆 | `memory.enabled` / `retrieval.mode` / `retrieval.alpha` / `retrieval.embedder` | true / substring / 0.5 / hashing |
| 断点 | `checkpoint.enabled` / `interval_steps` / `on_prune` / `detect_drift` | true / 4 / true / true |
| 安全 | `safety.hitl_policy` / `dedup_enabled` / `repeat_guard.*` / `shell.allow_commands` / `deny_patterns` | prompt / true / {max_repeat:2, window_size:12, window_max:4, count_cache_hits:true} / 14 命令白名单 / 10 模式黑名单 |
| 编排 | `orchestrator.max_rounds` / `max_retries` / `parallel` / `max_total_tokens` / `planner_mode` / `roles.*` | 3 / 2 / 1 / 800000 / deterministic / 角色模型路由与温度 |
| 工件 | `artifacts.root` / `redact_artifacts` / `sft_log` | .agentmuster/artifacts / true / false |
| 工具 | `tools.mcp.server_cmd` / `timeout` | 空（不启用）/ 30s |
| 服务 | `api.host/port` / `logging.format` / `observability.enabled` | 127.0.0.1:8910 / text\|json / true |

完整清单以 `agentmuster/config.py` 的 DEFAULT 字典与 `config/default.yaml` 注释为准。

## 7.5 评测跑法

```bash
# 离线五层(全离线确定性,秒级)
python -m agentmuster eval --suite all --output .agentmuster/eval

# 真实模型(Layer 6)与三臂对照(Layer 6b)——需本地 Ollama
python examples/real_model_demo.py
python -m agentmuster eval --suite real_baseline --output .agentmuster/real

# Layer 7 多智能体基准(手动,不进 CI)
python -m agentmuster.eval.layer7_multiagent --suite quick --backend local_openai --model qwen3.5:2b
python -m agentmuster.eval.layer7_multiagent --suite full --ablate guard,retry     # 机制消融
```

## 7.6 常见排错

| 现象 | 原因与处置 |
| --- | --- |
| `run` 报路径逃逸 | 工具参数写了绝对路径或 `..`；工作区沙箱在拦截——用相对路径或 `--workspace` 扩边 |
| Ollama 连不上 | `base_url` 端口不对（Ollama 11434 / llama.cpp 8080 / vLLM 8000）；先跑 `doctor` |
| 模型总是 text_json 降级 | 端点对 tools 请求回 400；检查端点是否支持 function calling |
| thinking 模型空转/截断 | 配 `max_tokens` 限幅；截断自愈会翻倍重试一次；必要时换非 thinking 模型 |
| 监控页任务列表空 | stdlib 实现无真列表；用 `--impl fastapi` 或靠单任务轮询 |
| Windows 控制台乱码 | 项目内已强制子进程 UTF-8；若自写脚本遇到，设置 `PYTHONIOENCODING=utf-8` |

***

# 第八部分：测试与质量保障

## 8.1 测试全景（349 项 / 24 文件）

构成（与 CHANGELOG 勾稽：272 基座 → ①+36=308 → ②+19=327 → ③+14=341 → ④+7=348 → 实测修复+1=349）：

| 测试域 | 代表文件 | 覆盖行为 |
| --- | --- | --- |
| 主循环 | test_harness.py | run/resume、空终答重问（触发/预算耗尽/可关闭）、控制收口 |
| 编排 | tests/orchestrator/ 六文件 | S1-S14 场景：单轮闭环、驳回→replan、checklist 兜底、空任务重问、依赖调度、失败重试+教训注入、重试耗尽绕行、预算熔断、并行隔离、编排 resume、确定性退化、submit_result/request_block 收口 |
| 状态机 | test_state_machine.py | 合法/非法迁移、attempts 计数、序列化往返 |
| 安全 | test_safety/test_policy/test_repeat_guard/test_control_tools | 15 个路径 payload fail-closed 不变量、8 个脱敏绕过变体、shell 注入 payload、Guard 三规则、白名单越权回灌 |
| 模型 | test_models/test_local_openai_protocol | 脚本推进/游标恢复、HTTP 桩协议状态机 6 用例（降级/自愈/解析）、超时重试回归 |
| 工具 | test_tools/test_sandbox/test_mcp | 工具行为、五步沙箱链、真实子进程 MCP 往返 6 用例 |
| 上下文/记忆/断点 | test_context/test_context_pairing/test_memory/test_vectors/test_checkpoint | 三级裁剪、配对不变量、哈希去重、三模式检索、恢复与漂移 |
| 评测 | test_eval/test_eval_layer7/test_real_baseline | 五层口径、**回归灵敏度**（注入退化必须显著下跌）、Layer 7 检查器/消融映射/冒烟 |
| API/可观测 | test_api/test_observability | 双实现端点、SSE 契约、span 树、OTel 桥接不崩 |

**离线确定性纪律**（贡献指南三条设计原则之一）：涉及模型调用的测试一律 MockBackend 或 monkeypatch；新能力默认关闭或零依赖实现，不得破坏既有测试的确定性。conftest.py 把 pytest tmp 重定向到仓库内 `.pytest_tmp`（规避 Windows 权限），并经 `clean_subprocess_env` 消毒子进程环境。

安全测试的 fail-closed 不变量值得单独记（`test_safety.py:19-27, 100-111`）：15 个真实路径遍历 payload（URL 编码 `%2e%2e%2f`、`..%c0%af`、`....//`、UNC `\\server\share`、260 个点、全角 `．．/`）的断言不是「必须被输入层拒绝」，而是「**要么 guard 拒绝，要么 resolve 的最终路径经 commonpath 验证仍在 root 内**」——因为编码/全角变体不保证在输入层解码，但不变量必须守住。

## 8.2 CI 与覆盖率门禁

`.github/workflows/ci.yml`：push main + 全部 PR 触发；矩阵 **ubuntu-latest + windows-latest × Python 3.11/3.12**（fail-fast: false）；步骤：checkout → setup-python（pip 缓存）→ 装 requirements-dev/api + `pip install -e . --no-deps` → `ruff check` → `mypy agentmuster tests` → `pytest --cov` → `python scripts/check_coverage.py coverage.json`。

**双阈值门禁**（`scripts/check_coverage.py`）：pytest-cov 不支持按路径分别 fail_under，故 coverage 配 `fail_under=0`，由脚本断言——全局 ≥75%（实测 80.4%），编排层 `agentmuster/orchestrator/**` + `agentmuster/agent/orchestrator.py` ≥90%（实测 94.9%，对该组文件**聚合**重算而非取最小值）。脚本输出全 ASCII（`[OK]/[FAIL]`）并 `sys.stdout.reconfigure(encoding="utf-8")` 双保险——CI 修复链的产物。

## 8.3 CI 跨平台修复链（run1→run5 全绿，现成面试素材）

| # | 症状 | 根因 | 修复 |
| --- | --- | --- | --- |
| 1 | Linux 上 pytest 崩于 coverage combine DataError | pytest-cov 的 `COV_CORE_*` 环境变量遗传给测试内启动的子进程（Layer 7 检查器/MCP fake server），子进程写出与主进程分支模式不一致的覆盖率数据 | 三个子进程出生点统一经 `util.clean_subprocess_env()` 消毒 |
| 2 | Windows MCP 子进程中文乱码 | 子进程按 locale（cp1252）写 stdio | 强制 `PYTHONIOENCODING/PYTHONUTF8=utf-8` |
| 3 | Linux 沙箱漏放 `..\evil` | Windows 风格反斜杠在 POSIX 是合法文件名 | `Workspace.resolve` 反斜杠归一为分隔符——安全边界跨平台一致 |
| 4 | Windows runner 打不出 `✓` 与中文 | cp1252 控制台 | 门禁脚本输出全 ASCII + stdout reconfigure 兜底 |

这一条链的价值不在修了四个 bug，而在方法论：**双 OS 矩阵是缺陷探测器**——四个问题在单平台上永远发现不了；每个修复都带回归测试固化。

***

# 第九部分：设计模式回顾与一页总图

读完 12 站，把用到的模式收拢（面试「你用过哪些设计模式」的具体答案）：

| 模式 | 在本项目中的落点 |
| --- | --- |
| 工厂 + 依赖注入 | `AgentHarness.build` / `build_registry` / `create_backend`——测试递假的即可隔离 |
| 策略 | 三档摘要器 / 四种审批 Provider / 三种检索模式 / 双 API 实现——接口不变换实现 |
| 责任链 | SafetyGuard 九检查点——每道防线独立、可插拔、短路返回 |
| 状态机 | 任务五状态 + 迁移表硬约束 + 非法迁移抛异常——把 LLM 输出约束进合法空间 |
| 观察者（事件总线） | `on_event` 一对多广播：Tracer/SSE/评测器零侵入挂接 |
| 适配器 | `_LegacyPlannerAdapter`（旧式 planner 接新接口）；`MCPProxyTool`（远端工具适配本地 Tool 基类） |
| 代理 | MCP 代理工具——本地调用透明转发远端，安全链无感 |
| 哨兵 | SSE 队列 `__done__` 标记流结束 |
| 模板方法（近似） | `role_system_message` 的「身份层 + 上下文层 + 协议层」三段组装 |
| 数据快照 / 事务写入 | checkpoint 自包含快照 + `atomic_write` 临时文件替换 |
| 契约测试 / 不变量回归 | `test_context_pairing`（配对不变量）、fail-closed 路径不变量、回归灵敏度锚 |

**一页总图（背下来）**：

```
                    ┌─────────────── [评测七层] ───────────────┐
                    │  L1-5 Mock回放(系统能力) · L6/6b 真实+三臂  │
                    │  L7 多智能体基准+机制消融(客观检查器)        │
                    └───────────────┬────────────────────────┘
                                    │ 只改 Config 开关
   CLI ──┐                  ┌──────┴───────┐        ┌────────────┐
   API ──┼── build() ──→    │ AgentHarness │←─ new ─│Orchestrator│
   WEB ──┘   (工厂+DI)       │  主循环×N步   │  每子任务 │ 多轮闭环   │
                    ┌────────┴──────────────┴────┐   └─────┬──────┘
                    │ ContextManager(三级裁剪)     │   状态机·Checklist
                    │ StructuredMemory(三层+检索)  │   RetryArchive·快照
                    │ CheckpointStore(六时机+漂移) │   WorkingMemory
                    │ SafetyGuard(九检查点纵深链)   │   预算熔断·双门验收
                    │ artifacts+Tracer(事件总线)   │
                    └────────────┬───────────────┘
                     ┌───────────┴───────────┐
                MockBackend(确定性)   LocalOpenAIBackend
                (系统能力度量)        (重试/SSE流式/协议降级/截断自愈)
```
***

# 第十部分：简历展示与面试准备（求职专用）

> 你说得对的部分：面试的胜负手是**核心代码与核心流程**。本部分的每个答案都锚定到具体源码位置——被追问时你能「翻到那几行」讲出来，这比背概念高一个量级。

## 10.1 这个项目证明什么能力

| 项目机制 | 证明的岗位能力 | 面试一句话 |
| --- | --- | --- |
| Harness 主循环 + 双后端抽象 | Agent 系统架构设计 | 「我把 Agent 需要什么拆成了可替换的六层」 |
| 三级裁剪 + 配对不变量 + token 估算 | 长上下文工程 | 「压缩率与信息保留率必须同时考核」 |
| 三层记忆 + 混合检索 | RAG/记忆系统 | 「follow-up 重读 2 次降到 0，MRR 0.44→0.98」 |
| 九检查点安全链 + 沙箱 + 脱敏 | 工具治理与安全 | 「模型输出不可信是公理，拦截原因回灌是手段」 |
| 多轮编排闭环 + 状态机 + 双门验收 | 多智能体系统 | 「LLM 只做决策，状态机与 Checklist 做兜底」 |
| 断点/漂移/快照双层恢复 | 可靠性工程 | 「宁可漂移误报，不可基于过期状态续跑」 |
| 七层评测 + 三臂对照 + 消融 | 评测体系与方法论 | 「固定其余、只动一个变量，每个机制都有对照数字」 |
| 零依赖 + Mock 回放 + CI 矩阵 | 工程质量意识 | 「349 项测试全离线，双 OS 矩阵当缺陷探测器」 |
| sft_collector + kb_lora | 数据飞轮/微调闭环 | 「Agent 跑任务沉淀样本，QLoRA 微调后接回验证」 |

## 10.2 简历写法

**项目一句话（两个版本，按 JD 侧重选）**：

- 系统版：*AgentMuster —— 面向代码仓库长链路任务的本地 Agent 运行底座：单 Agent Harness（上下文治理/结构化记忆/断点恢复/纵深安全链）+ Planner-Executor-Validator 多智能体编排闭环 + 七层评测体系，核心仅依赖 PyYAML，349 项测试全离线可复现。*
- 效果版：*从零手写 Coding Agent Harness 并建立对照实验评测体系：上下文平均压缩率约 80% 且信息保留 100%、follow-up 重复读文件 2→0、检索 MRR 0.44→0.98、三臂对照证明 harness 使 2B 模型硬断言通过率 1/4→4/4。*

**STAR 要点（挑 3-4 条展开，勿全堆）**：

1. **多智能体编排层**：设计 Planner-Executor-Validator 多轮闭环，任务五状态机硬约束 + Completion Checklist 客观验收（LLM 判定 ∧ 清单全满足的双门）+ 失败轨迹压缩归档并注入重试上下文；在 2B 真实模型上跑通多子任务接力交付（Layer 7 客观检查器验证运行产物而非 Agent 自述）。
2. **长上下文治理**：实现软预算折叠/硬限额截断/强制收缩三级策略链与 OpenAI tool_calls 配对不变量回归；平均压缩率约 80%，预算内完成率 100%，信息保留率 100%。
3. **工具安全纵深链**：动作白名单→JSON Schema 校验→路径沙箱（反斜杠归一/commonpath 防逃逸）→shell 黑白名单→去重→重复振荡三重检测→HITL 审批→输出脱敏；拦截原因回灌驱动模型自我纠偏。
4. **评测体系**：建立 Layer 1-7 评测与三种对照（系统开关 A/B、有无框架三臂、机制消融），冻结基准（固定 seed 落盘入库）保证跨提交可复现；用三臂对照量化框架价值（1/4→4/4），用消融开关量化单机制贡献。
5. **CI 跨平台工程**：双 OS × 双 Python 矩阵 + 双阈值覆盖率门禁（编排层 ≥90%）；定位并修复覆盖率环境变量遗传、Windows cp1252 编码、POSIX 反斜杠穿越等四类跨平台缺陷，每项配回归测试。

**技术关键词**（按 JD 筛选投放）：Agent Harness / Function Calling / Tool Use / MCP（Model Context Protocol）/ Multi-Agent Orchestration / RAG & Hybrid Retrieval（BM25 + 向量）/ Context Window Management / Checkpoint & Resume / LLM Evaluation（A/B、ablation、LLM-as-judge）/ SFT & QLoRA / SSE / FastAPI / pytest & CI。

## 10.3 三分钟项目陈述（背稿骨架）

> 「这个项目解决四个真实故障：上下文爆窗、重复劳动、中断丢状态、跑完说不清。结构是三层：**单 Agent 底座**——主循环每步做组装上下文、调模型、过九检查点安全链、执行工具、沉淀记忆、落断点；**多智能体编排**——Planner 拆解出带可验收标准的子任务，依赖就绪的并行执行，Validator 按验收清单逐项核对，验收双门是『模型判定与清单全满足同时成立』，缺失项精确回流触发增量重规划，失败任务压缩归档成教训注入重试；**七层评测**——前五层用 Mock 回放只测系统能力，第六层接真实本地模型，6b 做有无框架的三臂对照，第七层对多智能体基准做机制消融。
>
> 两个我最满意的取舍：一是**确定性优先**——核心只依赖 PyYAML，token 估算、摘要、Mock 回放全部确定性，所以 349 项测试全离线可复现，评测数据固定 seed 冻结入库；二是**如实度量**——三臂对照同时摆出成功率和 token 代价（1/4→4/4 的代价是 prompt token 从 529 涨到 11.6 万），LLM 评委不可靠就写进报告，不修改口径凑分。
>
> 工程上最有含金量的一段是 CI 跨平台修复链：双 OS 矩阵暴露了四类单平台永远发现不了的问题——覆盖率环境变量遗传给子进程、Windows cp1252 编码、POSIX 上反斜杠穿越漏拦、控制台打不出 Unicode——每类都修了并配了回归测试。」

（可控时间版本：第一段 60 秒讲结构与问题，第二段 60 秒讲两个取舍，第三段 45 秒讲 CI 链 + 数据飞轮收尾。）

## 10.4 高频面试题与完整回答要点（锚定源码版）

**基础层（考察概念是否真懂）**

1. **单次调用、工具循环、完整 Harness 的区别？** 单次调用无状态；工具循环加了「模型点菜-代码执行-结果回填」的循环；Harness 在循环外再加状态管理、上下文预算、安全链、断点、工件与评测。数据支撑：工具循环把 2B 模型通过率从 1/4 提到 3/4，完整治理再补到 4/4——每层贡献可量化（`eval/raw_baseline.py` 三臂报告）。
2. **上下文超限怎么办？** 三级策略链（`context/manager.py:107-168`）：`fold_old_turns`（保留最近 6 轮原文，其余折叠进 `# 历史摘要`）→ `drop_stale_turns`（仍超 6000 硬限则只留最近 1 轮）→ `truncate_long_content`（先按 8000 字符头尾截断、再循环把最长消息缩到 60%，下限 40 字符——保证 100% 落硬限内）。关键不变量：assistant.tool_calls 与 tool 消息必须原子成对（拆散=API 400），所以**按轮折叠而不是按条消息**——`test_context_pairing.py` 把这条不变量固化成回归测试。
3. **怎么防止工具调用死循环？** 两条机制协作（`guard.py:180-206` + `repeat_guard.py`）：去重缓存（`_dedup_key = name + sort_keys(params)` JSON，同参数短路由返回缓存）+ 振荡 Guard 三重检测（连续重复第 3 次拦、12 步窗口内同指纹 ≥4 次拦、A→B→A→B 周期振荡拦，指纹 = sha256(排序 JSON)）。精妙处：去重命中**也计入 Guard 指纹**（`count_cache_hits=True`），否则「反复重读同一文件」会被去重层放行永远到不了 Guard。
4. **MCP 是什么，你怎么接的？** 跨进程工具标准协议。我用零依赖 stdio JSON-RPC 2.0 客户端（`tools/mcp_client.py`）：Popen 起 server（stderr=DEVNULL、`clean_subprocess_env()` 消毒）→ `initialize` 握手（协议版本 2024-11-05）→ `notifications/initialized` → `tools/list`；Windows 管道不支持 select，所以读侧用**后台线程 + queue.Queue 实现带超时等待**；`MCPProxyTool` 把远端 inputSchema **零转换**赋给 `Tool.parameters`（同是 JSON Schema），name 加 `mcp_` 前缀防冲突；失败发 `mcp_unavailable` 事件降级纯内置工具，绝不打断主流程；远端工具与内置工具走同一套 SafetyGuard。
5. **为什么手写编排而不用 LangChain？** 三个理由：对每次裁剪/调用/落盘要有完全控制权（确定性可复现）；Harness 的核心难点在框架里是被隐藏的；「手写过并知道与框架的差异」比「用过」有说服力。可补：LangGraph 的 checkpoint 语义与本项目编排快照的异同。

**进阶层（考察设计取舍）**

6. **怎么让多 Agent 不「谎报完成」？** 四道防线：(1) 任务状态机约束合法迁移（`ALLOWED_TRANSITIONS` 迁移表，非法迁移抛 `IllegalTransitionError`）；(2) Checklist 逐项 evidence，`apply_verdict` 忽略未知 item_id 防幻觉编号；(3) 代码级双门 `completed = bool(data.get("completed")) and checklist.is_complete`（`validator.py:63-64`）——模型口头说完成且清单全满足才算过；(4) 端到端评测用客观检查器（真实 subprocess 执行产物并断言，如 `check_calc` 真的 `python -c "from calc import ...; assert ..."`），完全不采信 Agent 自述。
7. **子任务之间怎么共享与隔离？** `_build_harness`（`agent/orchestrator.py:400-424`）五条边界：**工作区共享**（`.orch_<id>/ws`，dep-chain 类复合目标要求后任务用先任务产出）、**记忆/工件隔离**（`memory_{task.id}` / `artifacts_{task.id}`）、**断点键隔离**（键含子任务 id）、**观测汇流**（子任务事件加 `sub` 标签并入编排事件流）、**白名单收窄**（`task.extra["allow_tools"]` ∪ 控制动作恒追加）。好故事：批次①按完全隔离实现，批次④跑 dep-chain 发现拆散了数据链，改成共享交付工作区——机制服从任务语义。
8. **断点恢复为什么还要漂移检测？** 断点只是「我的记忆」，工作区可能被外部改过；基于过期状态续跑会产生灾难性合并。做法（`checkpoint/drift.py:45-51`）：快照存「路径→SHA256」指纹表，恢复时三集合运算（modified/added/deleted）。取舍：whitespace 变化也报漂移（误报）——宁可误报不可漏报（`eval/runner.py:498-500` 注释明写）。
9. **怎么评估 harness 有没有用（而不是模型强）？** 三臂对照（`eval/raw_baseline.py`）：固定模型与任务集，single_shot（单次调用+代码块提取）/naive_loop（朴素循环，**刻意不复用**治理/记忆/断点/安全审批/去重——这正是它与 harness 的差异）/harness 三臂；成功率的跃升就是框架贡献（1/4→3/4→4/4）。再进一步用机制消融（`--ablate guard,retry,budget,validator`，把机制放宽到永不触发）量化单机制边际贡献。评测纪律：Mock 回放测系统能力、真实端点测模型能力，口径分离互不冒充。
10. **小模型（2B）有什么工程问题，怎么兜的？** 五个：空终答（`empty_answer_nudges` 温和重问一次，`harness.py:336-368`）；输出截断（`finish_reason=length` 时 2×max_tokens 自愈重试，上限 32768，`local_openai.py:127-134`）；不支持 function calling（NATIVE→TEXT_JSON 单向降级，工具目录进 system 消息，四级候选解析文本动作）；思考型模型烧 max_tokens（限幅 4096）；结构化输出不合法（`structured_complete` 反馈重试环：把解析错误回灌让模型重发，最多 3 次）。加一个网络层：`socket.timeout` 不是 URLError，需单独捕获否则穿透重试循环——Layer 7 实测发现，回归测试固化。
11. **重试怎么避免重复踩坑？** Retry Archive（`orchestrator/retry_archive.py`）：失败轨迹 LLM 压缩成「根因+下次策略」（`FAILURE_COMPRESS_PROMPT`，≤250 字，异常回退截断 2000），按任务分桶 append 不覆盖；重试时 `render_for_task` 渲染成「== Retry Archive:本任务的历史失败记录(务必避免重蹈覆辙)==」经 `TaskInput.extra["retry_lessons"]` 注入 harness 的 memory_block（`harness.py:286-291`）——第二次尝试的 system 区里就有学费清单。
12. **成本怎么算的？** `CostTracker.cost_of`（`cost.py`）纯函数：`prompt/1000×输入单价 + completion/1000×输出单价`，价目表支持通配键 `*` 兜底；harness 每步模型调用即算（`harness.py:327`），metrics 与报告透出 `cost_usd`；未配置返回 0 不打扰离线运行。

**深挖层（考察源码级理解，挑 2-3 个准备）**

13. **审批 Provider 和 guard.check 的关系？** check 只打 `needs_approval` 标记（`danger==HITL`，`guard.py:208-211`），真正裁决在 harness 调 `guard.approve(gr.action)` → Provider（Prompt 交互 input y/N / AllowAll / DenyAll / Callback）；且**去重短路优先于审批**——重复的 HITL 命令第二次直接回缓存（`cached_output` 分支的 `needs_approval=False`），不再次骚扰人工。
14. **为什么 ContextManager 每次全量重算而不是增量折叠？** 确定性可重放：同一历史能以不同预算无限次重放（Layer 2 三臂就是这么跑的），增量折叠的状态漂移不可逆。实现：`assemble()` 在 `copy.deepcopy` 的消息上裁剪，绝不改 `raw_turns`（`manager.py:108-112` docstring 明写）。代价是深拷贝内存开销——单任务 ~30 步可接受。
15. **编排级 resume 和单任务 resume 语义差别？** 单任务是步级续接（`start_step=step_index`、`backend.load_state` 游标复位、raw_turns 逐轮重建）；编排快照是任务/轮级（`{goal, round_no, validated, tasks, checklist, archive}`，不含子任务轨迹），resume 对 PENDING 任务从零重跑（带教训），RUNNING 中的任务在快照里仍是 PENDING——「重做未竟」而非「步级续接」，首版刻意简化（MERGE_DESIGN 开放点 O1）。`Task.from_dict` 恢复时绕过状态机校验——快照状态是历史事实。
16. **SSE 链路怎么保证不漏不挂？** 后台 daemon 线程执行、`finally: bus.done(task_id)` 保证 `__done__` 哨兵必达；队列 get 超时 15s 发 `: keep-alive` 注释行心跳；客户端断开不再消费但哨兵仍触发正常结束不泄漏事件循环；stdlib 无 SSE 时前端 `onerror` 降级轮询；`event.setdefault("task_id", ...)` 补全路由键。
17. **token 估算准吗？** 不追求与真实 tokenizer 一致，追求**单调+稳定**（中文每字 1 token、其余 `(other+3)//4` 向上取整、每消息 +4 结构开销，`context/tokens.py`）；真实 usage 到了就用真实值，缺失才回退启发式（completion 用 tokenize_len、prompt 用裁剪后 token 占位）。一致性来自「永远同一把尺子」。
18. **Layer 7 为什么不进 CI？** 依赖真实本地模型，CI 必须零模型依赖零下载；CI 里只跑它的机制单测（检查器单测/消融映射/mock 冒烟——mock 必然 rc==1 但验证评测机本身完整落盘）。

## 10.5 如实边界与改进方向（诚实应答是加分项）

被问到局限时的标准应答（先承认、再给原因、最后给方案）：

| 边界 | 应答要点 |
| --- | --- |
| Layer 6 的 LLM 评委 0/4 不可靠 | 2B 模型当评委判不出对错；设计上评委只是硬断言之上的否决项，报告如实保留不以硬断言冒称评委通过；改进：换更大评委模型/多评委投票/评委偏差校准 |
| Layer 7 quick 3/4 | fizzbuzz 失败是 thinking 模型把 max_tokens 烧在思考上被截断——判定为小模型能力边界而非管道缺陷；改进：关 thinking/加长超时/换 qwen3:4b |
| 三臂对照 token 代价大 | harness 臂 prompt token 11.6 万 vs 朴素循环 1.4 万——框架的 token 花在历史回填与记忆注入上；改进：上下文治理已把平均压缩到 80%，可进一步做工具结果选择性回填 |
| 单任务层无并行工具执行 | 同轮多个 tool_calls 顺序执行（每轮上限 8 个）；改进：读类工具可并行 |
| 编排预算熔断粗粒度 | token 只在子任务结束后回填（`_run_single:331-334`），长任务可超预算后才熔断；BLOCKED→RUNNING 边存在但未启用——改进：步内熔断 + BLOCKED 任务复活路径 |
| 测试盲区 | sft_collector 无专门测试文件；CLI 无独立测试文件（间接覆盖） |
| `subtask_end` 可能重复/矛盾发射 | 失败重试路径 `_handle_failure` 发一次 FAILED、循环外又发一次 PENDING（`_run_single:355-356`）——成功路径只发一条所以测试计数恰好掩盖 |

**反问环节可抛的问题**（展示视野）：「你们 Agent 的评测是怎么把系统能力和模型能力分开的？」「工具调用的安全边界在你们那里是硬拦截还是提示词约束？」「多轮任务的验收标准怎么防模型乐观推断？」

## 10.6 作品集组合建议

若简历同时放多个 Agent 项目，建议的叙事分工：本项目讲**工程底座**（Harness、治理、评测、CI——「我知道 Agent 系统每个部件怎么做、怎么验」）；垂直场景项目讲**业务落地**（RAG、风控闭环、多端架构——「我能把 Agent 技术用到一个真实领域里」）。两句话合并的定位：*能从零设计并验证 Agent 运行底座，也能把它落地成带安全闭环的业务系统。*
***

# 附录 A：事件类型全集（SSE/trace 可观测面）

**Harness 8 种**（`agent/harness.py` 各 `_emit` 调用点）：

| 事件 | 字段 | 发射点 |
| --- | --- | --- |
| `task_start` | task_id, follow_up_of, reason, ts | `_run` 启动（:296） |
| `step_start` | index, ts | 每步 assemble 后（:316） |
| `model_call` | index, model, prompt_tokens, completion_tokens, latency_ms, ts | 模型调用后（:328） |
| `step_end` | index, ts | 终答分支与工具分支两处（:346/:383） |
| `tool_call` | step_index, name, status, latency_ms, ts | 每个工具执行后（:502） |
| `checkpoint` | step, reason, task_id, ts | 每次 `_checkpoint`（:592） |
| `control_end` | action, status, ts | 控制信号消费处（:414） |
| `task_end` | status, ts | 收尾（:451） |

**只写 trajectory 不发事件的四种**：`empty_answer_nudge`（:365）、`max_steps`（:419）、`error`（:425）、`interrupt`（:311）。

**编排层 16 种**（`agent/orchestrator.py`）：`orchestration_start / orchestration_resume / orchestration_round_start / orchestration_round_end(result=accept|reject) / orchestration_validate_error / orchestration_plan / orchestration_replan / orchestration_validated / budget_exceeded / deps_invalid / subtask_start / subtask_end / subtask_blocked / subtask_control / task_retry_scheduled / orchestration_end`；子任务事件加 `sub` 标签透传。EventBus **无类型白名单**——新增事件天然可达 SSE。

**消费端**：Tracer 消费 7 种重建 span 树（`step_end/control_end` 隐式收口）；监控页渲染 7 种并专门格式化 model_call/tool_call/checkpoint。

# 附录 B：已知不一致与待办清单（读源码时用它当镜子）

以下是文档与代码、代码与代码之间的**真实出入**（面试高级谈资，也是 PR 的现成候选）：

1. **README「完全隔离工作区」已过时**：README 子代理编排一节与 `agent/orchestrator.py` 模块 docstring（:5）仍写「工作区/记忆/断点/工件互不污染」，但批次④修正后代码是**编排内共享交付工作区**（`_build_harness:404-411` 注释与 test_loop S1/S10 可证）——同文件内 docstring 与 :404 的修正注释自相矛盾。
2. **README 防线口径不一**：第 27 行「七道防线」漏了第 0 道动作白名单，第 275 行「六道防线」又漏了振荡 Guard；真实顺序见 5.2 节。
3. **README 路径笔误**：`agent/agent/orchestrator.py` 应为 `agentmuster/agent/orchestrator.py`。
4. **「Layer 7」编号复用**：`eval/runner.py:697` 的嵌入器对照（`--suite embedder`）与 `layer7_multiagent.py` 多智能体基准都自称 Layer 7。
5. **TESTING.md 已过时**：仍写「项目当前不依赖远端 CI」，实际 ci.yml 已恢复双 OS 矩阵。
6. **ARCHITECTURE.md 编排段部分滞后**：「Orchestrator(子代理编排)」小节仍描述旧的一次性分解语义与完全隔离根。
7. **`subtask_end` 可能重复/矛盾发射**：失败重试路径 `_handle_failure`（:363-364）发一次 FAILED、`_run_single` 循环外（:355-356）又发一次 PENDING——同一次执行两条状态矛盾的事件；成功路径只发一条，`test_loop.py` S1 的 `types.count("subtask_end") == 2` 恰好掩盖。
8. **空终答在确定性编排模式下可能被标 DONE**：nudge 耗尽后 status=completed、final_answer 为空；LLM 模式 Validator 双门会拦，但 `_auto_verdict` 只看状态不看内容。
9. **冻结生成数据的 wrong_hit 播种错位**：`generators.py:235-238` 场景计划用短名 `wrong`/`fresh`，而播种与严格判定分支只认 `wrong_hit`/`fresh_hit`（`runner.py:428,438`）——生成数据的 wrong follow-up 实际未被播种诱饵（手写数据正常）。
10. **tests/orchestrator/test_loop.py 的 S9 缺号**：注释声称 S1-S14，实际无 S9 用例。
11. **角色层 `_emit` 未包异常抑制**：`planner.py:29-31`、`validator.py:38-40` 与 Orchestrator/Harness 的防御风格不一致，on_event 抛异常会打断规划调用（验收阶段会被降级逻辑接住，plan 阶段会直接抛出）。
12. **event_bus 的 `drop()` 从未被调用**：任务结束后队列滞留注册表，后来的 SSE 订阅者只收到心跳，与 404 文案「stream already ended」不完全一致。

# 附录 C：学习自测总清单

**L1 · 概念层（能说清）**

- [ ] 用自己的话说清 Harness 与工具循环的区别（各举两个本项目机制）
- [ ] 软预算与硬限额的区别；三级裁剪各自何时触发
- [ ] 安全链的真实顺序（含第 0 道白名单与前置控制分流）与各自拦截后的行为
- [ ] 状态机五状态与三条特殊转移边的语义
- [ ] 三种「对照」（开关 A/B / 三臂 / 消融）各回答什么问题

**L2 · 机制层（能画图/能推演）**

- [ ] 白板画出一次 run 的完整时序（含 checkpoint 六时机与 8 种事件）
- [ ] 推演「模型连续 3 次读同一文件」在安全链中的完整路径（去重命中→指纹计数→Guard 拦截）
- [ ] 推演一轮「验收驳回→重规划→二轮通过」的全过程（事件名、快照时机、missing 注记）
- [ ] 说清两层 checkpoint 的键、粒度、恢复语义差异
- [ ] 说清 HashingEmbedder 为什么用 MD5 而不是内建 hash

**L3 · 工程层（能动手/能评审）**

- [ ] 不看文档写一个带 script 的任务 JSON 并跑通 run/resume
- [ ] 加一个自定义工具（继承 Tool、注册、观察它在安全链中的行为）
- [ ] 跑 `eval --suite all` 并解读 report.md 的每个指标
- [ ] 独立找出附录 B 中的至少 3 处不一致并给出修复 PR 思路
- [ ] 用 `--ablate` 跑一次消融并解释结果差异

# 附录 D：FAQ

**Q：必须联网吗？** 不需要。核心只依赖 PyYAML，Layer 1-5 与全部 pytest 用 MockBackend 离线跑通；只有真实模型评测与 FastEmbedEmbedder 需要本地/网络模型服务。

**Q：支持哪些模型？** 任何 OpenAI 兼容端点：Ollama/vLLM/llama.cpp；协议不兼容时自动降级 TEXT_JSON 文本协议。

**Q：会误改我仓库的文件吗？** 工具受 `workspace.root` 沙箱约束，路径逃逸/绝对路径/符号链接被拦截；shell 走白名单且默认需人工审批；工件统一写 `.agentmuster/`（建议加入 .gitignore）。

**Q：为什么指标大多来自 MockBackend？** 这样度量的才是系统能力：同一份脚本输入下只有系统开关在变。模型能力由 Layer 6/6b/7 在固定模型与任务集上单独评估——口径分离、互不冒充。

**Q：学习顺序怎么排最省力？** 先跑通（第七部分 7.1-7.2，30 分钟）→ 第 8 站主循环 + 5.2 安全链（建立主干）→ 按需展开其余站。不要按目录字母序读。

**Q：和直接学 LangChain 比呢？** 互补。框架教「怎么快速组装」，本项目教「组装的每个零件为什么存在、失效时怎么查」。面试官问到框架深水区（checkpoint 语义、裁剪策略、评测口径）时，手写过的人答得出来。

**Q：文中的代码摘录可靠吗？** 全部摘自 `main` 分支当前版本真实源码（行号一致），仅个别处为讲清主干删节（标 `…`）。源码与文档冲突时以源码为准——这本身就是读代码的正确姿势。
***

# 附录 E：测试即规格——关键测试代码精读

> 对核心代码最有说服力的补充是**测试代码**：它们是核心机制的可执行规格。面试被追问「你怎么知道它真的有效」时，引用测试断言比引用实现更有力。以下精读四个最有代表性的测试文件。

## E.1 test_context_pairing.py — 配对不变量的回归（58 行全读）

```python
"""上下文配对不变量回归(D9:固化"裁剪不得破坏 tool_calls/tool 配对")。

来源:miniMaster 的 LiveContextTrimmer 组件不移植(MERGE_DESIGN 决策 D9),
但其 tool_calls 配对边界用例改写为本回归测试——按「轮」折叠的 ContextManager
在结构上保持 assistant.tool_calls ↔ tool(tool_call_id) 原子对应,本测试把
这条不变量固化,防止未来引入按条消息裁剪的策略时破坏配对(破坏会导致 API 400)。
"""

def _assert_paired(messages: list) -> None:
    """断言 OpenAI tool-calling 协议的配对不变量:
    (a) 全部 tool 消息的 tool_call_id 集合 == 全部 assistant tool_calls 的 id 集合;
    (b) 每条 tool 消息前方必须存在发起该 id 的 assistant 消息。"""
    tool_ids: set[str] = set()
    call_ids: set[str] = set()
    seen_calls: set[str] = set()
    for m in messages:
        role = m.role if hasattr(m, "role") else m["role"]
        if role == "assistant":
            for c in (m.tool_calls if hasattr(m, "tool_calls") else m["tool_calls"]) or []:
                call_ids.add(c["id"])
                seen_calls.add(c["id"])
        elif role == "tool":
            tid = m.tool_call_id if hasattr(m, "tool_call_id") else m["tool_call_id"]
            tool_ids.add(tid)
            assert tid in seen_calls, f"tool 消息 {tid} 前方缺少发起它的 assistant 消息"
    assert tool_ids == call_ids, f"配对破坏: tool={tool_ids} calls={call_ids}"
```

两个用例：「80 token 紧预算下裁剪仍配对」（把硬限压到极小，逼三级裁剪全部触发）与「无裁剪全保留」。这就是 D9 决策「不要组件、要教训」的落地形态——**被放弃的组件以不变量的形式永生**。

## E.2 tests/orchestrator/test_loop.py — S1-S14 编排场景（372 行）

每个场景 = MockBackend 脚本回放 + 精确事件断言，覆盖编排层的全部行为。场景清单（测试即规格）：

| # | 场景 | 关键断言 |
| --- | --- | --- |
| S1 | 单轮闭环 | success=True、rounds=1、**两任务产物并存于同一共享工作区**（批次④语义）、checklist 全 `[x]` |
| S2 | 验收驳回→replan→二轮通过 | rounds=2、有 `orchestration_replan` 事件、新增任务 id 递增 |
| S3 | planner 输出无 checklist | 从任务 done_criteria 派生 items，验收可达 |
| S4 | planner 空任务 | structured_complete 重试环，第二条消息含反馈文案 |
| S5 | 依赖调度 B depends_on [A] | A 先于 B；环形/自依赖被 sanitize 剔除 + `deps_invalid` 事件 |
| S6 | 失败重试+教训注入 | **第二次执行的模型消息里含 "Retry Archive" 字样**；archive 记录 1 条 |
| S7 | `max_retries=0` 重试耗尽 | 任务终态 FAILED，replan 收到「拆成更小步骤」缺失项 |
| S8 | `max_total_tokens=1` 预算熔断 | PENDING→BLOCKED + `budget_exceeded` 事件 + validator 缺失回流 |
| S10 | parallel=2 并行隔离 | 共享交付目录产物并存；StructuredMemory 并发 save 无交错 |
| S11 | 编排 resume | DONE 任务不重跑、Validator 补验收通过、发 `orchestration_resume` |
| S12 | 确定性退化 | 单任务单轮完成，旧行为兼容 |
| S13 | `submit_result` 收口 | 子任务 DONE、`subtask_control` 事件 |
| S14 | `request_block` | BLOCKED → replan 绕行 |

S6 是「Retry Archive 教训注入」的端到端证明——**断言的不是归档文件存在，而是第二次尝试的模型输入里真的能看到教训**。

## E.3 test_repeat_guard.py — 三重规则的边界与集成（107 行）

规则单测之外，最值得注意的是**集成测试**（:78-91）——「去重缓存命中也计入 Guard 指纹」：

```python
    def test_dedup_cache_hits_count_toward_guard(self):
        # 同一 file_read 连续调用:第 1 次(真实执行) -> 第 2 次(去重缓存命中,
        # 但指纹计入) -> 第 3 次(去重命中且指纹达到 max_repeat+1 -> Guard 拦截)
        …
        # 去重缓存命中也计入指纹(反复重读同一内容同样是刷步行为)
        if self.repeat_guard is not None and self._count_cache_hits:
            verdict = self.repeat_guard.check(tool.name, params)
```

这验证的是**两条防线的交接语义**：没有这个集成断言，「反复重读」会在去重层被静默放行——单测各自全绿但组合有洞。面试讲「测试策略」时，这是「集成测试测的是交互语义而非功能」的现成例子。

## E.4 test_safety.py — fail-closed 不变量与脱敏绕过变体

15 个路径 payload 的 fail-closed 断言模式（:19-27）：

```python
PATH_PAYLOADS = [
    "../escape.txt", "..\\escape.txt", "/etc/passwd", "C:\\Windows\\system32",
    "%2e%2e%2fescape.txt", "..%c0%afescape.txt", "....//escape.txt",
    "\\\\server\\share\\evil.txt", "…" * 130, "．．/escape.txt",   # 全角/超长/UNC
    …
]

def test_path_payloads_fail_closed(...):
    for payload in PATH_PAYLOADS:
        # 不变量:要么 guard 拒绝,要么 resolve 的最终路径仍在工作区内
        try:
            resolved = workspace.resolve(payload)
            assert os.path.commonpath([str(workspace.root), str(resolved)]) == str(workspace.root)
        except PathEscapeError:
            pass  # 被拒绝也是安全行为
```

8 个脱敏绕过变体（大小写 KEY、冒号无空格、行尾、Bearer、password=、`secret :`、RSA 私钥块）断言「原密文不再出现」。shell 注入 payload（`; rm -rf /`、`$(...)`、反引号、`${IFS}`、base64 管道、nc 反弹）断言 `not allowed or needs_approval`——**要么拦截、要么至少升级为人工审批**，不要求二选一的具体路径。

# 附录 F：面试白板题演练（「现场写一下」参考实现）

> Agent 岗位二面常考「现场写」。以下 5 道题全部取材自本项目核心代码——先把参考实现写熟，再练脱稿。

## F.1 「实现一个滑动窗口死循环检测」

考点：对应 `safety/repeat_guard.py`。参考要点（可手写的最小版）：

```python
from collections import deque
import hashlib, json

class RepeatGuard:
    def __init__(self, max_repeat=2, window=12, window_max=4):
        self.max_repeat, self.window, self.window_max = max_repeat, window, window_max
        self._last, self._consec = None, 0
        self._hist = deque(maxlen=window)

    def check(self, action, args):
        fp = hashlib.sha256(json.dumps({"a": action, "args": args},
                                       sort_keys=True).encode()).hexdigest()
        self._consec = self._consec + 1 if fp == self._last else 1
        self._last = fp
        self._hist.append(fp)
        if self._consec > self.max_repeat:                 # 规则1:连续重复
            return False, "consecutive"
        if self._hist.count(fp) >= self.window_max:        # 规则2:窗口计数
            return False, "window"
        h = list(self._hist)
        for p in (2, 3):                                   # 规则3:周期振荡
            if len(h) >= 2*p and all(h[-1-i] == h[-1-p-i] for i in range(p)):
                return False, "cycle"
        return True, ""
```

追问预判：「为什么指纹用 sha256 而不是内建 hash？」（Python 哈希随机化跨进程不确定）「窗口计数和连续重复为什么都要？」（后者拦 3 连，前者拦 12 步内 4 次的交替刷步）「拦截后给模型什么？」（带策略引导语的回灌文本）。

## F.2 「实现历史折叠：保留最近 N 轮，其余折叠为摘要」

考点：对应 `context/manager.py` 的 `fold_old_turns`。参考要点：

```python
def fold(history: list[dict], keep: int, summarize) -> list[Message]:
    msgs = []
    folded, visible = history[:-keep], history[-keep:]
    if folded:
        msgs.append(Message("system", "# 历史摘要\n" + summarize(folded)))
    msgs.extend(copy.deepcopy(flatten(visible)))
    return msgs
```

追问预判：「为什么 deep copy？」（不污染 raw_turns，同一历史可按不同预算重放——评测确定性）「为什么按轮折叠不按条消息？」（OpenAI 协议要求 tool 消息与 assistant.tool_calls 配对，按轮折叠结构上不可能拆散——`test_context_pairing.py`）「折叠后仍超限怎么办？」（drop_stale_turns 只留最近 1 轮 → truncate_long_content 循环缩最长消息）。

## F.3 「实现原子写文件（跨平台）」

考点：对应 `util.atomic_write`。参考要点：

```python
def atomic_write(path, content: str):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        for attempt in range(8):
            try:
                os.replace(tmp, p)          # 同分区 rename,原子
                return
            except PermissionError:         # Windows:杀软/索引服务短暂占用
                if attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
```

追问预判：「为什么不直接 `path.write_text`？」（写一半崩溃留半截文件——断点/指标文件不可容忍）「为什么要重试 PermissionError？」（Windows 真实事故：杀软短暂锁文件）。

## F.4 「实现一个带验收双门的循环」

考点：对应 `agent/orchestrator.py` 轮循环骨架。参考要点（伪代码级）：

```python
for round_no in range(1, max_rounds + 1):
    execute_ready_tasks()                          # PENDING 且依赖就绪;失败轮内重入队
    verdict = validator.verify(goal, checklist, tasks)
    if verdict.completed and checklist.is_complete:   # 双门:LLM 判定 ∧ 清单全满足
        success = True; break
    missing = verdict.missing_requirements + blocked_failed_notes(tasks)
    if round_no == max_rounds:
        break
    new = planner.replan(goal, tasks, missing, activity=log.tail(8))
    if not new and not any(t.status is PENDING for t in tasks):
        break                                       # 死局检测
    tasks.extend(new); sanitize_deps()
```

追问预判：「为什么必须双门？」（LLM 自述「应该完成了」不算——乐观推断防线）「missing 为什么要拼接 BLOCKED/FAILED 注记？」（把「没完成」升级为「需绕行/需拆小」的可执行修复指令）「死局检测防什么？」（replan 空转烧 token）。

## F.5 「实现 SSE 推流：心跳 + 哨兵」

考点：对应 `api/fastapi_server.py` 的事件生成器。参考要点：

```python
async def gen(q):
    while True:
        try:
            evt = await loop.run_in_executor(None, lambda: q.get(timeout=15))
        except Empty:
            yield ": keep-alive\n\n"                        # 注释行做心跳
            continue
        if evt.get("type") == "__done__":                   # 哨兵 → 具名事件关流
            yield "event: done\ndata: {\"type\":\"done\"}\n\n"
            break
        yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
```

追问预判：「为什么用哨兵不用直接 close？」（正常收尾语义，前端 `addEventListener('done')` 触发终态拉取）「为什么要心跳？」（代理/网关会掐静默连接）「为什么 get 放 executor？」（阻塞队列操作不能卡事件循环）。

## F.6 MERGE_DESIGN 决策表 D1-D11（面试讲「合并工程」的底稿）

| # | 决策点 | 结论 |
|---|--------|------|
| D1 | 子任务执行架构 | 单循环改造：角色机制注入 AgentHarness，不引入第二套主循环 |
| D2 | Orchestrator 语义 | 多轮闭环（执行→Checklist 验收→replan）；run(goal) 签名兼容 |
| D3 | 仓库形态 | 新仓库 AgentMuster，继承 mycoder 全部 git 历史 |
| D4 | 原仓库处置 | mycoder 原样不动；miniMaster 本地 git 快照 24f4247 |
| D5 | 包名 | 批次①内 mycoder → agentmuster（机械重命名独立成提交） |
| D6 | 版本与依赖 | Python ≥3.11；核心保持「仅 PyYAML」零依赖叙事 |
| D7 | CI | 完整恢复：双 OS 矩阵 + ruff + mypy + pytest + 覆盖率门禁（编排层 ≥90%，全局 ≥75%） |
| D8 | 角色视图记忆 | WorkingMemory 拆解移植（只留 Planner/Validator 视图） |
| D9 | LiveContextTrimmer | 不移植组件；其 tool_calls 配对边界用例改写为回归测试 |
| D10 | 编排层断点续跑 | 进批次①：编排快照复用 CheckpointStore |
| D11 | 节奏 | 分 5 批合入，每批全量测试绿 + CHANGELOG 条目 |

讲合并叙事的万能句式：「每个决策背后都有一个『如果不这么做会怎样』——D1 防两套安全链、D9 防重复实现与不可测、D11 防大爆炸合并。」
# 附录 G：面试前速记卡（开场前 10 分钟过一遍）

## G.1 关键数字表（背下来，张口就来）

| 数字 | 含义 | 出处 |
| --- | --- | --- |
| 30 / 8 / 1 | `max_steps` / 每轮工具上限 / 空终答重问次数 | `config.py` harness 节 |
| 6000 / 6 / 8000 | 硬限 token / 保留最近轮数 / 单消息截断字符 | `config.py` context 节 |
| 4 | checkpoint 间隔步数（相对恢复起点） | `checkpoint.interval_steps` |
| 3 / 2 / 1 / 800000 | 编排 max_rounds / max_retries(共 3 次执行) / parallel / token 预算 | `config.py` orchestrator 节 |
| 2 / 12 / 4 | Guard 连续重复阈值 / 窗口步数 / 窗口内上限 | `safety.repeat_guard.*` |
| 0.5→8s ×3 | 模型重试退避（base/cap/次数） | `local_openai.py:31-34` |
| 32768 | 截断自愈的 max_tokens 天花板 | `max_tokens_ceiling` |
| 2026-08-19 | 冻结基准 seed | `benchmarks/generators.py` |
| 349 项 / 24 文件 | pytest 总量 | 实测 collect |
| 80.4% / 94.9% | CI 覆盖率：全局 / 编排层（门禁 75% / 90%） | check_coverage.py 实测 |
| 1/4 → 3/4 → 4/4 | 三臂对照硬断言通过率（qwen3.5:2b） | Layer 6b 报告 |
| 529 → 14,564 → 115,919 | 三臂 prompt token（single_shot/naive_loop/harness） | Layer 6b 报告 |
| 28%→63% / 0.44→0.98 | 检索 recall@3（substring→hybrid）/ MRR@5（n=82） | Layer 5 报告 |
| ~80% / 100% / 100% | 上下文压缩率 / 预算内完成率 / 信息保留率 | Layer 2 报告 |
| 2→0 / 100% | follow-up 重读次数 / 漂移识别准确率（45 场景） | Layer 3/4 报告 |
| 8 任务 / quick 3/4 | Layer 7 多智能体基准 / 首次真实实测 | layer7_multiagent.py |
| 14 + 10 | shell 白名单命令数 / 黑名单模式数 | `config.py` safety.shell |

## G.2 核心代码锚点表（被追问时「翻到那几行」）

| 机制 | 文件:行 |
| --- | --- |
| 主循环（终答/工具/控制收口/for-else） | `agent/harness.py:306-419` |
| 空终答温和重问 | `agent/harness.py:336-368` + 常量 :86-89 |
| 工具前置分流（控制工具） | `agent/harness.py:478-486` |
| 安全链九检查点 | `safety/guard.py:148-211` |
| 参数校验五项 | `safety/guard.py:29-51` |
| shell 黑白名单 | `safety/guard.py:226-239` |
| 去重键（排序 JSON） | `safety/guard.py:222-224` |
| 振荡三重检测 + 周期判定 | `safety/repeat_guard.py:51-102, 104-111` |
| 沙箱五步链 | `tools/sandbox.py:30-54` |
| 指纹快照 os.walk 剪枝 | `tools/sandbox.py:89-117` |
| file_edit 唯一匹配纪律 | `tools/file_tools.py:87-107` |
| MCP 握手 + 零转换注册 | `tools/mcp_client.py:45-72, 153-167` |
| 三级裁剪 + 硬兜底 | `context/manager.py:107-151, 153-168` |
| token 估算（CJK 1 字/其余 4 字符） | `context/tokens.py:14-37` |
| 摘要器三档与回退 | `context/summarizer.py:28-81` |
| 记忆哈希去重 | `memory/store.py:127-132` |
| follow-up 注入 | `memory/store.py:182-194` |
| HashingEmbedder（MD5 桶） | `memory/vectors.py:79-96` |
| hybrid α 融合 | `memory/vectors.py:258-269` |
| 断点快照八字段 | `agent/harness.py:566-593` |
| 漂移三集合运算 | `checkpoint/drift.py:45-51` |
| 原子写 + Windows 重试 | `util.py:48-71` |
| Mock 脚本协议 | `models/mock.py:59-86` |
| 重试退避 + TimeoutError 单捕 | `models/local_openai.py:208-254` |
| 协议降级 + 截断自愈 | `models/local_openai.py:105-135` |
| SSE 流式累积（index 分桶） | `models/local_openai.py:137-188` |
| 编排轮循环（双门/回流/死局） | `agent/orchestrator.py:178-227` |
| 工作队列 + 预算熔断 | `agent/orchestrator.py:250-273` |
| 失败收口 + 重试重入队 | `agent/orchestrator.py:359-373` |
| 子任务装配五边界 | `agent/orchestrator.py:400-424` |
| 状态机迁移表 | `orchestrator/tasks.py:21-27` |
| Checklist 双门 + 未知项忽略 | `orchestrator/validator.py:63-64` + `checklist.py:24-39` |
| 结构化输出反馈重试环 | `orchestrator/structured.py:19-41` |
| 编排快照键与恢复语义 | `orchestrator/snapshot.py:20-58` |
| SSE 生成器（心跳+哨兵） | `api/fastapi_server.py:185-198` |
| 双后端决策优先级 | `api/fastapi_server.py:39-51` |
| Tracer 事件分发 + latency 反推 | `observability/tracing.py:127-178` |
| SFT 采集触发条件 | `agent/harness.py:436-446` + `sft_collector.py:23-50` |
| 客观检查器（subprocess 断言） | `eval/layer7_multiagent.py` 各 `check_*` |
| 消融映射 | `eval/layer7_multiagent.py:216-234` |
| judge 严格 JSON + 解析失败判负 | `eval/judge.py:39-82` |

## G.3 一句话机制表（30 秒电梯版弹药）

- **确定性**：Mock 脚本回放 + 启发式 token + 深拷贝重算——「同输入必得同输出」。
- **裁剪**：按轮折叠保配对；压缩率与信息保留率双指标。
- **记忆**：SHA256 一致即跳过——「重读归零」的底层保证。
- **安全**：九检查点纵深链；一切拦截变文本回灌，安全链同时是教学链。
- **防死循环**：去重管重复、Guard 管模式，缓存命中也计指纹。
- **验收**：双门 = LLM 判定 ∧ 清单全满足；评测端再加客观检查器（运行产物而非自述）。
- **重试**：失败压缩成教训注入重试上下文——「学费清单」。
- **恢复**：两层 checkpoint；恢复先查工作区漂移（宁可误报不可漏报）。
- **可观测**：on_event 一条总线三类消费者（轨迹/trace/SSE）；埋点异常全吞。
- **评测**：固定其余只动一个变量；三臂定框架价值、消融定机制贡献、灵敏度回归防自证。
- **成本**：三臂同时亮成功率和 token 代价——「如实度量」。

## G.4 三个最容易翻车的细节（答错暴露没读过代码）

1. **「脱敏在执行前还是执行后？」**——执行后、回灌上下文前（输出侧），且工件导出/SFT 采集多点再脱敏。
2. **「去重命中第二次 HITL 命令还要审批吗？」**——不要，去重短路优先于审批，直接回缓存。
3. **「编排 resume 会步级续接子任务吗？」**——不会，RUNNING 子任务在快照里是 PENDING，整任务重跑（带教训）；子任务自身 checkpoint 独立可用但不被编排自动调用（开放点 O1）。
***

# 附录 H：全文件一句话索引（nav 用）

> 66 个源码文件的速查表。找「某件事在哪做」时先查这里，再跳对应站点精读。

| 文件 | 行数 | 一句话 |
| --- | --- | --- |
| `config.py` | 191 | DEFAULT 字典 + 深合并 + 点路径 get/set |
| `state.py` | 105 | 纯 dataclass：Message/ToolCall/Step/TaskInput/RunResult |
| `util.py` | 169 | truncate/atomic_write/extract_json/parse_text_action/clean_subprocess_env |
| `artifacts.py` | 234 | Metrics 累加器 + RunRecorder 轨迹 + report.md 渲染（时间线反推） |
| `tasks.py` | 36 | 任务文件加载（.json / .md frontmatter） |
| `cost.py` | 39 | CostTracker 价目表核算（通配键 `*`） |
| `sft_collector.py` | 73 | 成功任务采集 (instruction,output,context) 样本 |
| `cli.py` | 235 | 8 子命令入口；CLI 覆盖经 cfg.set 后打 |
| `models/base.py` | 60 | ModelBackend 抽象 + state()/load_state() 断点钩子 |
| `models/mock.py` | 96 | 脚本回放，游标 {turn, call_seq} 可恢复 |
| `models/local_openai.py` | 390 | urllib + 重试退避 + SSE 流式 + 协议降级 + 截断自愈 |
| `tools/base.py` | 91 | Tool 基类（danger 三档）+ ToolRegistry |
| `tools/sandbox.py` | 129 | Workspace 五步沙箱 + snapshot 指纹 + os.walk 剪枝 |
| `tools/file_tools.py` | 172 | file_read/write/edit/list + grep_search |
| `tools/shell_tool.py` | 53 | shell_exec（cwd 锁定 + timeout≤30s + 环境消毒） |
| `tools/memory_tool.py` | 30 | memory_query（查三层记忆） |
| `tools/control_tools.py` | 53 | submit_result/request_block（占位 stub，分发前拦截） |
| `tools/mcp_client.py` | 198 | stdio JSON-RPC 客户端 + MCPProxyTool 零转换注册 |
| `safety/guard.py` | 239 | 九检查点链 + validate_params + 四种审批 Provider |
| `safety/policy.py` | 65 | Role/Action/ActionPolicy 动作白名单 |
| `safety/repeat_guard.py` | 118 | 三重死循环检测（连续/窗口/周期） |
| `safety/redact.py` | 36 | 6 类敏感信息正则脱敏 |
| `context/tokens.py` | 37 | CJK 1 字/其余 4 字符的 token 估算 |
| `context/summarizer.py` | 89 | Deterministic/LLM/Noop 三摘要器 |
| `context/manager.py` | 171 | 组装 + 三级裁剪链（深拷贝重算） |
| `memory/store.py` | 338 | 三层记忆 + SHA256 去重 + followup 注入 + 检索入口 |
| `memory/vectors.py` | 272 | HashingEmbedder/VectorIndex/BM25/HybridRetriever |
| `checkpoint/store.py` | 52 | 极薄断点存取（atomic_write） |
| `checkpoint/drift.py` | 51 | 漂移三集合运算 |
| `agent/harness.py` | 633 | 主循环总装（全书核心） |
| `agent/orchestrator.py` | 440 | 多轮闭环总装（全书核心） |
| `agent/prompts.py` | 108 | Planner/Validator 身份层+协议层模板（叶子模块） |
| `orchestrator/tasks.py` | 109 | 任务状态机（迁移表硬约束） |
| `orchestrator/checklist.py` | 77 | CompletionChecklist（空清单不算完成） |
| `orchestrator/structured.py` | 41 | structured_complete 反馈重试环 |
| `orchestrator/planner.py` | 120 | plan（空任务语义重问）/ replan（增量续号） |
| `orchestrator/validator.py` | 73 | verify + 代码级双门 |
| `orchestrator/working_memory.py` | 59 | 角色视图渲染 + 有界活动日志（线程安全） |
| `orchestrator/retry_archive.py` | 59+11 | 失败分桶归档 + 教训渲染注入 |
| `orchestrator/snapshot.py` | 58 | 编排快照（复用 CheckpointStore） |
| `observability/tracing.py` | 250 | 事件驱动 span 树 + OTLP 风格导出 + OTel 桥接 |
| `api/server.py` | 179 | stdlib 零依赖实现（同步阻塞，遗留端点） |
| `api/fastapi_server.py` | 229 | 异步提交 + SSE + /api/compare 双跑 |
| `api/event_bus.py` | 54 | 按 task_id 路由的队列桥 + done 哨兵 |
| `api/monitor_page.py` | 207 | 内嵌 Vue 3 监控页（零构建） |
| `eval/runner.py` | 773 | Layer 1-5 + _check_expect 统一断言 |
| `eval/benchmark.py` | 34 | 手写+冻结合并加载 |
| `eval/experiment.py` | 32 | compare_metrics/format_delta 对照原语 |
| `eval/judge.py` | 82 | LLM 评委（解析失败即判负） |
| `eval/real.py` | 131 | Layer 6 三重与判定（completed∧断言∧judge） |
| `eval/raw_baseline.py` | 436 | 三臂对照（single_shot/naive_loop/harness） |
| `eval/layer7_multiagent.py` | 370 | Layer 7 客观检查器 + 消融 |

---

*本文档基于 `main` 分支 `f2aba60`（2026-10）撰写；349 项测试、CI 双 OS 矩阵、覆盖率 80.4%/94.9% 为当前实测基线。*
