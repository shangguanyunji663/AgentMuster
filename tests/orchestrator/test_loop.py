"""多轮闭环场景测试(MockBackend 脚本回放,零外部依赖)。

覆盖 MERGE_DESIGN §7.1 的 S1-S12:正常闭环 / 验收驳回重规划 / checklist 兜底
派生 / planner 空任务重问 / 依赖调度与非法依赖清理 / 失败重试与教训注入 /
重试耗尽绕行 / 全局预算熔断 / 并行隔离 / 编排 resume / 确定性退化。
"""
from __future__ import annotations

import json
from pathlib import Path

from agentmuster.agent.orchestrator import Orchestrator
from agentmuster.config import Config
from agentmuster.models import MockBackend
from agentmuster.orchestrator.planner import PlannerRole
from agentmuster.orchestrator.validator import ValidatorRole


def json_response(obj) -> dict:
    return {"content": json.dumps(obj, ensure_ascii=False)}


def _config(tmp_path, **overrides) -> Config:
    cfg = Config()
    cfg.set("workspace.root", str(tmp_path / "ws"))
    cfg.set("memory.root", str(tmp_path / "memory"))
    cfg.set("checkpoint.root", str(tmp_path / "checkpoints"))
    cfg.set("artifacts.root", str(tmp_path / "artifacts"))
    for k, v in overrides.items():
        cfg.set(k, v)
    return cfg


def _file_backend(path: str, content: str, answer: str = "完成") -> MockBackend:
    return MockBackend.from_recipe(
        [{"name": "file_write", "arguments": {"path": path, "content": content}}], answer=answer)


def _plan(*tasks, checklist=None) -> dict:
    data = {"tasks": list(tasks)}
    if checklist is not None:
        data["checklist"] = checklist
    return data


def _verdict(completed: bool, evidence: str = "已核实") -> dict:
    return {"items": [{"item_id": f"C{i}", "satisfied": completed, "evidence": evidence}
                      for i in (1, 2)],
            "completed": completed,
            "missing_requirements": [] if completed else ["尚未满足"],
            "summary": "通过" if completed else "未过"}


T1 = {"id": "T1", "title": "创建问候文件", "description": "写 hello.txt",
      "done_criteria": "hello.txt 存在且内容为 hi"}
T2 = {"id": "T2", "title": "创建计数文件", "description": "写 count.txt",
      "done_criteria": "count.txt 存在"}


# ---- S1 单轮闭环 ----
def test_s1_single_round_close_loop(tmp_path):
    events: list[dict] = []
    plan_resp = json_response(_plan(T1, T2, checklist=["hello 为 hi", "count 存在"]))
    planner = PlannerRole(MockBackend(script=[plan_resp]), events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(True))]), events.append)

    def factory(task):
        return _file_backend("hello.txt", "hi") if task.id == "T1" else _file_backend("count.txt", "0")

    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("创建两个文件")
    assert art["success"] is True and art["rounds"] == 1
    assert all(i["satisfied"] for i in art["checklist"]["items"])
    ws = Path(tmp_path) / "ws" / f".orch_{art['task_id']}" / "ws"  # 编排内共享交付目录
    assert (ws / "hello.txt").read_text(encoding="utf-8") == "hi"
    assert (ws / "count.txt").exists()
    types = [e["type"] for e in events]
    assert "orchestration_plan" in types and "orchestration_validated" in types
    assert types.count("subtask_end") == 2


# ---- S2 验收驳回 → replan → 二轮通过 ----
def test_s2_replan_after_reject(tmp_path):
    events: list[dict] = []
    plan = _plan({"id": "T1", "title": "写 hello", "description": "d",
                  "done_criteria": "hello.txt 内容为 hi"},
                 checklist=["hello.txt 内容为 hi"])
    replan = {"analysis": "内容不对,需重写",
              "tasks": [{"id": "T2", "title": "修正内容", "description": "重写为 hi",
                         "done_criteria": "hello.txt 内容为 hi"}]}
    planner = PlannerRole(MockBackend(script=[json_response(plan), json_response(replan)]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(False, "内容不是 hi")),
                                                  json_response(_verdict(True, "内容正确"))]),
                              events.append)

    def factory(task):
        return _file_backend("hello.txt", "wrong") if task.id == "T1" \
            else _file_backend("hello.txt", "hi")

    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("写 hello 文件")
    assert art["success"] is True and art["rounds"] == 2
    assert any(e["type"] == "orchestration_replan" for e in events)
    ws = Path(tmp_path) / "ws" / f".orch_{art['task_id']}" / "ws"
    assert (ws / "hello.txt").read_text(encoding="utf-8") == "hi"  # T2 在共享目录修正 T1 的产出


# ---- S3 checklist 缺失时从 done_criteria 兜底派生 ----
def test_s3_checklist_fallback_derivation(tmp_path):
    events: list[dict] = []
    planner = PlannerRole(MockBackend(script=[json_response(_plan(T1))]), events.append)
    accept = {"items": [{"item_id": "C1", "satisfied": True, "evidence": "ok"}],
              "completed": True, "missing_requirements": [], "summary": "通过"}
    validator = ValidatorRole(MockBackend(script=[json_response(accept)]), events.append)
    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=lambda t: _file_backend("hello.txt", "hi"),
                        on_event=events.append)
    art = orch.run("写 hello")
    assert art["success"] is True
    assert art["checklist"]["items"][0]["text"].startswith("任务 T1 达成")


# ---- S4 planner 空任务语义重问 ----
def test_s4_planner_empty_tasks_reask(tmp_path):
    events: list[dict] = []
    planner = PlannerRole(MockBackend(script=[json_response({"tasks": [], "checklist": []}),
                                              json_response(_plan(T1, checklist=["hello 为 hi"]))]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(True, "单项通过"))]),
                              events.append)
    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=lambda t: _file_backend("hello.txt", "hi"),
                        on_event=events.append)
    art = orch.run("写 hello")
    assert art["success"] is True  # 重问后产出任务并完成


# ---- S5 依赖调度 + 非法依赖清理 ----
def test_s5_dependency_order_and_sanitize(tmp_path):
    events: list[dict] = []
    order = []
    t2 = dict(T2, depends_on=["T1"])
    t3 = {"id": "T3", "title": "坏依赖", "description": "d", "done_criteria": "c",
          "depends_on": ["T9", "T3"]}  # 指向不存在任务 + 自依赖
    plan_resp = json_response(_plan(T1, t2, t3, checklist=["c1", "c2", "c3"]))
    planner = PlannerRole(MockBackend(script=[plan_resp]), events.append)
    verdict = {"items": [{"item_id": f"C{i}", "satisfied": True, "evidence": "ok"} for i in (1, 2, 3)],
               "completed": True, "missing_requirements": [], "summary": "通过"}
    validator = ValidatorRole(MockBackend(script=[json_response(verdict)]), events.append)

    def factory(task):
        order.append(task.id)
        return MockBackend(script=[{"content": f"完成 {task.id}"}])

    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("依赖调度")
    assert art["success"] is True
    assert any(e["type"] == "deps_invalid" and e["task"] == "T3" for e in events)
    assert order[0] == "T1"  # 依赖 T1 的 T2 必须晚于 T1 启动
    assert set(order) == {"T1", "T2", "T3"}


# ---- S6 失败重试 + Retry Archive 教训注入 ----
class _FlakyBackend(MockBackend):
    """首次调用抛异常(模拟端点故障),之后按脚本走;捕获最近一次 messages。"""

    def __init__(self, script, answer, fail_times=1):
        super().__init__(script=script, default_answer=answer)
        self.fail_times = fail_times
        self.last_messages = None

    def complete(self, messages, tools=None, temperature=0.0):
        self.last_messages = messages
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("模型端点故障(注入)")
        return super().complete(messages, tools, temperature)


def test_s6_retry_with_lessons_injection(tmp_path):
    events: list[dict] = []
    planner = PlannerRole(MockBackend(script=[json_response(_plan(T1, checklist=["hello 为 hi"]))]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(True))]), events.append)
    flaky = _FlakyBackend(
        script=[{"tool_calls": [{"name": "file_write", "arguments": {"path": "hello.txt", "content": "hi"}}]},
                {"content": "写好了"}],
        answer="写好了", fail_times=1)
    backends = {"T1": flaky}

    def factory(task):
        return backends[task.id]

    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("写 hello")
    assert art["success"] is True
    assert [s["attempts"] for s in art["subtasks"]] == [2]  # 失败一次后重试成功
    assert any(e["type"] == "task_retry_scheduled" for e in events)
    # 第二次尝试的上下文里必须注入了 Retry Archive 教训
    assert flaky.last_messages is not None
    assert any("Retry Archive" in str(getattr(m, "content", "")) for m in flaky.last_messages)


# ---- S7 重试耗尽 → replan 绕行 ----
def test_s7_retry_exhausted_then_bypass(tmp_path):
    events: list[dict] = []
    plan = _plan({"id": "T1", "title": "注定失败", "description": "d", "done_criteria": "c"},
                 checklist=["c1"])
    replan = {"analysis": "绕开坏任务", "tasks": [{"id": "T2", "title": "替代路径",
                                                   "description": "直接产出", "done_criteria": "c2"}]}
    planner = PlannerRole(MockBackend(script=[json_response(plan), json_response(replan)]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(False, "未过")),
                                                  json_response(_verdict(True, "通过"))]),
                              events.append)

    class _AlwaysFail(MockBackend):
        def complete(self, messages, tools=None, temperature=0.0):
            raise RuntimeError("模型端点故障(注入)")

    def factory(task):
        return _AlwaysFail() if task.id == "T1" else MockBackend(script=[{"content": "替代完成"}])

    cfg = _config(tmp_path)
    cfg.set("orchestrator.max_retries", 0)  # 无重试额度:一次失败即终态
    orch = Orchestrator(cfg, planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("绕行场景")
    assert art["success"] is True and art["rounds"] == 2
    t1 = next(s for s in art["subtasks"] if s["id"] == "T1")
    assert t1["status"] == "FAILED" and t1["attempts"] == 1
    assert not any(e["type"] == "task_retry_scheduled" for e in events)
    assert any(e["type"] == "orchestration_replan" for e in events)


# ---- S8 全局 token 预算熔断 ----
def test_s8_budget_exceeded_blocks_pending(tmp_path):
    events: list[dict] = []
    planner = PlannerRole(MockBackend(script=[json_response(_plan(T1, T2, checklist=["c1", "c2"])),
                                              json_response({"analysis": "预算耗尽,不新增任务",
                                                             "tasks": []})]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(False, "预算不足"))]),
                              events.append)
    cfg = _config(tmp_path)
    cfg.set("orchestrator.max_total_tokens", 1)  # 跑完第一个任务即超限
    orch = Orchestrator(cfg, planner=planner, validator=validator,
                        backend_factory=lambda t: MockBackend(script=[{"content": "完成"}]),
                        on_event=events.append)
    art = orch.run("预算熔断")
    t2 = next(s for s in art["subtasks"] if s["id"] == "T2")
    assert t2["status"] == "BLOCKED"
    assert any(e["type"] == "budget_exceeded" for e in events)
    assert art["success"] is False


# ---- S10 并行隔离 ----
def test_s10_parallel_isolation(tmp_path):
    events: list[dict] = []
    planner = PlannerRole(MockBackend(script=[json_response(_plan(T1, T2, checklist=["c1", "c2"]))]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(True))]), events.append)
    orch = Orchestrator(_config(tmp_path, **{"orchestrator.parallel": 2}),
                        planner=planner, validator=validator,
                        backend_factory=lambda t: _file_backend("hello.txt", "hi")
                        if t.id == "T1" else _file_backend("count.txt", "0"),
                        on_event=events.append)
    art = orch.run("并行两文件")
    ws = Path(tmp_path) / "ws" / f".orch_{art['task_id']}" / "ws"
    assert (ws / "hello.txt").exists()      # 共享交付目录:两任务产物并存
    assert (ws / "count.txt").exists()
    assert art["success"] is True
    assert [e["type"] for e in events].count("subtask_end") == 2


# ---- S11 编排层断点续跑 ----
def test_s11_resume_from_snapshot(tmp_path):
    events1: list[dict] = []
    cfg = _config(tmp_path)
    cfg.set("orchestrator.max_rounds", 1)  # 首轮验收未过即停,制造续跑场景
    planner = PlannerRole(MockBackend(script=[json_response(_plan(T1, checklist=["hello 为 hi"]))]),
                          events1.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(False, "内容需修正"))]),
                              events1.append)
    orch = Orchestrator(cfg, planner=planner, validator=validator,
                        backend_factory=lambda t: _file_backend("hello.txt", "hi"),
                        on_event=events1.append)
    art1 = orch.run("写文件")
    assert art1["success"] is False
    task_id = art1["task_id"]

    events2: list[dict] = []
    accept = {"items": [{"item_id": "C1", "satisfied": True, "evidence": "文件已在"}],
              "completed": True, "missing_requirements": [], "summary": "补验收通过"}
    orch2 = Orchestrator(cfg, planner=PlannerRole(MockBackend(script=[])),
                         validator=ValidatorRole(MockBackend(script=[json_response(accept)])),
                         backend_factory=lambda t: _file_backend("hello.txt", "hi"),
                         on_event=events2.append)
    art2 = orch2.resume(task_id)
    assert art2["success"] is True  # 已 DONE 的任务不重跑,Validator 补验收通过
    assert any(e["type"] == "orchestration_resume" for e in events2)
    assert all(i["satisfied"] for i in art2["checklist"]["items"])


# ---- S12 确定性退化(无 LLM planner,向后兼容) ----
def test_s12_deterministic_degradation(tmp_path):
    orch = Orchestrator(_config(tmp_path),
                        backend_factory=lambda t: _file_backend("hello.txt", "hi"))
    art = orch.run("写 hello.txt")
    assert art["success"] is True and art["rounds"] == 1
    assert art["subtasks"][0]["status"] == "DONE"
    assert art["checklist"]["items"][0]["satisfied"] is True  # 自动验收回填
    assert art["stop_reason"] == "Completion Checklist 验收通过"


# ---- S13 submit_result 收口 → DONE(批次② 控制动作) ----
def test_s13_submit_result_drives_done(tmp_path):
    events: list[dict] = []
    plan_resp = json_response(_plan(T1, checklist=["hello 为 hi"]))
    planner = PlannerRole(MockBackend(script=[plan_resp]), events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(True, "文件已在"))]),
                              events.append)
    sub = MockBackend(script=[
        {"tool_calls": [{"name": "file_write",
                         "arguments": {"path": "hello.txt", "content": "hi"}}]},
        {"tool_calls": [{"name": "submit_result",
                         "arguments": {"success": True, "summary": "hello.txt 已写入 hi"}}]},
    ])
    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=lambda t: sub, on_event=events.append)
    art = orch.run("写 hello")
    assert art["success"] is True
    assert art["subtasks"][0]["status"] == "DONE"
    assert art["subtasks"][0]["result_summary"] == "hello.txt 已写入 hi"
    assert any(e["type"] == "subtask_control" and e["action"] == "submit_result" for e in events)


# ---- S14 request_block 申报阻塞 → replan 绕行(批次②) ----
def test_s14_request_block_then_bypass(tmp_path):
    events: list[dict] = []
    plan = _plan({"id": "T1", "title": "需要外部权限", "description": "d",
                  "done_criteria": "拿到审批"},
                 checklist=["拿到审批或等效产出"])
    replan = {"analysis": "权限拿不到,改走无需审批的路径",
              "tasks": [{"id": "T2", "title": "替代方案", "description": "d",
                         "done_criteria": "等效产出完成"}]}
    planner = PlannerRole(MockBackend(script=[json_response(plan), json_response(replan)]),
                          events.append)
    validator = ValidatorRole(MockBackend(script=[json_response(_verdict(False, "未完成")),
                                                  json_response(_verdict(True, "替代完成"))]),
                              events.append)

    def factory(task):
        if task.id == "T1":
            return MockBackend(script=[{"tool_calls": [{"name": "request_block",
                                                        "arguments": {"reason": "缺少审批权限"}}]}])
        return MockBackend(script=[{"content": "替代完成"}])

    orch = Orchestrator(_config(tmp_path), planner=planner, validator=validator,
                        backend_factory=factory, on_event=events.append)
    art = orch.run("阻塞绕行")
    t1 = next(s for s in art["subtasks"] if s["id"] == "T1")
    assert t1["status"] == "BLOCKED"  # 执行者申报的外部阻塞
    assert art["success"] is True and art["rounds"] == 2
    blocked_events = [e for e in events if e["type"] == "subtask_blocked"
                      or (e["type"] == "subtask_end" and e.get("status") == "BLOCKED")]
    assert blocked_events
