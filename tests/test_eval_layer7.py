"""Layer 7 多智能体基准测试(离线:检查器单测 + 消融映射 + runner 机制冒烟)。"""
from __future__ import annotations

import json

import pytest

from agentmuster.config import Config
from agentmuster.eval.layer7_multiagent import (
    TASKS,
    ablation_overrides,
    check_bugfix,
    check_grep,
    check_notes,
    main,
    run_one,
    setup_bugfix,
    setup_grep,
)

# ---- 客观检查器单测(移植口径) ----

def test_check_notes_verifies_exact_lines(tmp_path):
    (tmp_path / "notes.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    ok, _ = check_notes(tmp_path)
    assert ok
    (tmp_path / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    ok, detail = check_notes(tmp_path)
    assert not ok and "['alpha', 'beta']" in detail


def test_check_bugfix_runs_assertions(tmp_path):
    setup_bugfix(tmp_path)
    ok, _ = check_bugfix(tmp_path)  # 未修复 → 断言失败
    assert not ok
    (tmp_path / "sum_to.py").write_text(
        'def sum_to(n):\n    return sum(range(1, n + 1))\n', encoding="utf-8")
    ok, _ = check_bugfix(tmp_path)
    assert ok


def test_check_grep_requires_exact_todo_list(tmp_path):
    setup_grep(tmp_path)
    ok, _ = check_grep(tmp_path)  # 未产出 todos.txt
    assert not ok
    (tmp_path / "todos.txt").write_text(
        "app/main.py\napp/io_utils.py\napp/report.py\n", encoding="utf-8")
    ok, _ = check_grep(tmp_path)
    assert ok


def test_task_suite_shape():
    assert len(TASKS) == 8
    ids = [t["id"] for t in TASKS]
    assert ids == ["hello", "notes", "calc", "fizzbuzz", "parallel-files",
                   "dep-chain", "bugfix", "codebase-grep"]
    assert all(callable(t["check"]) for t in TASKS)


# ---- 消融映射 ----

def test_ablation_overrides_mapping():
    assert ablation_overrides("retry") == {"orchestrator.max_retries": 0}
    assert ablation_overrides("budget") == {"orchestrator.max_total_tokens": 0}
    guard = ablation_overrides("guard")
    assert guard["safety.repeat_guard.max_repeat"] == 10**6
    assert ablation_overrides("validator") == {"orchestrator.planner_mode": "deterministic"}
    merged = ablation_overrides("guard,retry")
    assert set(merged) >= {"safety.repeat_guard.max_repeat", "orchestrator.max_retries"}
    with pytest.raises(SystemExit):
        ablation_overrides("bogus")


# ---- runner 机制冒烟(mock 后端:验证机械可跑、行结构完整、报告落盘) ----

def test_runner_smoke_writes_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("agentmuster.eval.layer7_multiagent.PROJECT_ROOT", tmp_path)
    rc = main(["--suite", "quick", "--backend", "mock", "--tag", "smoke"])
    assert rc == 1  # mock 后端无法真实完成任务 → 客观检查不过
    report = json.loads((tmp_path / "eval" / "results" / "smoke.json").read_text(encoding="utf-8"))
    assert report["tag"] == "smoke"
    assert [r["task"] for r in report["rows"]] == ["hello", "notes", "calc", "fizzbuzz"]
    for row in report["rows"]:
        assert set(row) >= {"success", "check_passed", "rounds", "attempts", "tokens",
                            "retries", "replans", "denied_actions", "check_detail"}
    assert "成功率" in capsys.readouterr().out


def test_run_one_returns_objective_row(tmp_path):
    setup_grep(tmp_path)
    cfg = Config()
    cfg.set("workspace.root", str(tmp_path))
    overrides = {"orchestrator.planner_mode": "deterministic",
                 "orchestrator.max_rounds": 1, "harness.max_steps": 4}
    row = run_one(TASKS[-1], tmp_path, overrides, "mock")
    assert row["task"] == "codebase-grep"
    assert row["success"] is False  # mock 完不成,但机械与检查器执行完毕
    assert row["check_passed"] is False
    assert "todos.txt 不存在" in row["check_detail"]
