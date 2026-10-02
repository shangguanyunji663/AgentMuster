"""Layer 7 多智能体端到端基准(批次④,移植自 miniMaster eval/run_eval.py,快照 24f4247)。

8 个标准任务 + 客观检查器(运行产物并验证,不采信 Agent 自述)+ 机制消融开关。
真实模型手动跑(不进 CI):

    python -m agentmuster.eval.layer7_multiagent --suite full
    python -m agentmuster.eval.layer7_multiagent --suite quick --ablate guard,retry
    python -m agentmuster.eval.layer7_multiagent --only bugfix --tag debug

指标:客观通过率 / 轮数 / 重试 / 重规划 / 被拦截动作 / token / 耗时。
结果写 eval/results/layer7_<tag>.json;工作区在 eval/workspaces/(均不入库)。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ..agent.orchestrator import Orchestrator
from ..config import Config
from ..models import create_backend
from ..util import clean_subprocess_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUICK_COUNT = 4
MAX_TASK_STEPS = 12
MAX_TASK_ROUNDS = 2


# ---- 检查器辅助 ----

def run_python(workdir: Path, script: str, *args: str, timeout: int = 60) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, script, *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=clean_subprocess_env(),
    )
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def read_file(workdir: Path, name: str) -> str:
    return (workdir / name).read_text(encoding="utf-8", errors="replace")


# ---- 任务定义(检查器全部客观:验证运行产物) ----

def check_hello(workdir: Path) -> tuple[bool, str]:
    if not (workdir / "hello.py").exists():
        return False, "hello.py 不存在"
    ok, out = run_python(workdir, "hello.py")
    return (ok and "Hello, AgentMuster!" in out), f"运行输出: {out.strip()[:80]}"


def check_notes(workdir: Path) -> tuple[bool, str]:
    try:
        lines = [ln.strip() for ln in read_file(workdir, "notes.txt").splitlines() if ln.strip()]
    except OSError:
        return False, "notes.txt 不存在"
    return lines == ["alpha", "beta", "gamma"], f"实际内容 {lines}"


def check_calc(workdir: Path) -> tuple[bool, str]:
    if not (workdir / "calc.py").exists():
        return False, "calc.py 不存在"
    ok, out = run_python(workdir, "-c",
                         "from calc import add, sub, mul, div;"
                         "assert add(2,3)==5 and sub(5,2)==3;"
                         "assert mul(3,4)==12 and div(8,4)==2; print('OK')")
    return (ok and "OK" in out), out.strip()[:100]


def check_fizzbuzz(workdir: Path) -> tuple[bool, str]:
    try:
        lines = read_file(workdir, "fizzbuzz_output.txt").splitlines()
    except OSError:
        return False, "fizzbuzz_output.txt 不存在"
    if len(lines) != 100:
        return False, f"行数 {len(lines)} != 100"
    if lines[14].strip() != "FizzBuzz":
        return False, f"第 15 行是 {lines[14]!r}"
    return True, "100 行且第 15 行为 FizzBuzz"


def setup_bugfix(workdir: Path) -> None:
    """植入一个带 off-by-one bug 的脚本,供任务修复。"""
    (workdir / "sum_to.py").write_text(
        'def sum_to(n):\n'
        '    total = 0\n'
        '    for i in range(1, n):  # bug: 漏掉 n 本身\n'
        '        total += i\n'
        '    return total\n',
        encoding="utf-8",
    )


def check_bugfix(workdir: Path) -> tuple[bool, str]:
    ok, out = run_python(workdir, "-c",
                         "from sum_to import sum_to;"
                         "assert sum_to(5) == 15 and sum_to(1) == 1 and sum_to(10) == 55;"
                         "print('OK')")
    return (ok and "OK" in out), out.strip()[:100]


def setup_grep(workdir: Path) -> None:
    """植入 5 个源文件,其中 3 个含 TODO 标记。"""
    files = {
        "app/main.py": "def main():\n    pass  # TODO: 入口逻辑\n",
        "app/util.py": "def fmt(x):\n    return str(x)\n",
        "app/io_utils.py": "def load(p):\n    # TODO: 异常处理\n    return open(p).read()\n",
        "app/consts.py": "MAX = 10\n",
        "app/report.py": "def render(rows):\n    # TODO: 分页\n    return '\\n'.join(rows)\n",
    }
    for name, content in files.items():
        path = workdir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_grep(workdir: Path) -> tuple[bool, str]:
    try:
        lines = {ln.strip() for ln in read_file(workdir, "todos.txt").splitlines() if ln.strip()}
    except OSError:
        return False, "todos.txt 不存在"
    expected = {"app/main.py", "app/io_utils.py", "app/report.py"}
    return lines == expected, f"实际 {sorted(lines)},期望 {sorted(expected)}"


def check_dep_chain(workdir: Path) -> tuple[bool, str]:
    try:
        data = json.loads(read_file(workdir, "data.json"))
        summary = read_file(workdir, "summary.txt").strip()
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"产物缺失或损坏: {exc}"
    ok, out = run_python(workdir, "read_data.py")
    expected_total = str(sum(item["score"] for item in data))
    return (ok and expected_total in summary and expected_total in out,
            f"summary={summary[:60]!r} 运行输出含总分 {expected_total}: {expected_total in out}")


def check_parallel(workdir: Path) -> tuple[bool, str]:
    try:
        lines = [ln for ln in read_file(workdir, "combined.txt").splitlines() if ln.strip()]
    except OSError:
        return False, "combined.txt 不存在"
    fizz = lines.count("Fizz")
    buzz = lines.count("Buzz")
    return (len(lines) == 10 and fizz == 5 and buzz == 5), \
        f"{len(lines)} 行(Fizzx{fizz}, Buzzx{buzz})"


TASKS: list[dict] = [
    {
        "id": "hello", "difficulty": "easy",
        "goal": "在当前工作目录创建 hello.py,运行时打印 Hello, AgentMuster!,然后运行验证",
        "check": check_hello,
    },
    {
        "id": "notes", "difficulty": "easy",
        "goal": "在当前工作目录创建 notes.txt,内容恰好三行:第一行 alpha,第二行 beta,"
                "第三行 gamma,然后读取验证",
        "check": check_notes,
    },
    {
        "id": "calc", "difficulty": "medium",
        "goal": "在当前工作目录创建 calc.py,实现 add/sub/mul/div 四个函数,并用命令运行断言验证:"
                "add(2,3)=5、sub(5,2)=3、mul(3,4)=12、div(8,4)=2",
        "check": check_calc,
    },
    {
        "id": "fizzbuzz", "difficulty": "medium",
        "goal": "创建 fizzbuzz.py:打印 1..100,3 的倍数输出 Fizz,5 的倍数输出 Buzz,两者倍数输出"
                " FizzBuzz;运行它并把全部输出保存到 fizzbuzz_output.txt,验证第 15 行是 FizzBuzz",
        "check": check_fizzbuzz,
    },
    {
        "id": "parallel-files", "difficulty": "medium",
        "goal": "创建两个相互独立的脚本 fizz.py(打印 5 行 Fizz)和 buzz.py(打印 5 行 Buzz);"
                "两者都创建完成后,依次运行它们,把两次运行的输出按顺序一次性合并写入 combined.txt"
                "(前 5 行 Fizz、后 5 行 Buzz,共 10 行)",
        "check": check_parallel,
        "overrides": {"orchestrator.parallel": 2},
    },
    {
        "id": "dep-chain", "difficulty": "hard",
        "goal": "分三步:1) 创建 data.json,内容为包含 3 条记录的数组,每条有 name 和 score 字段"
                "(score 自定);2) 创建 read_data.py,读取 data.json 并打印所有 score 的总分;"
                "3) 运行 read_data.py,并把它的输出内容保存到 summary.txt",
        "check": check_dep_chain,
    },
    {
        "id": "bugfix", "difficulty": "hard",
        "setup": setup_bugfix,
        "goal": "工作目录里的 sum_to.py 有 bug:sum_to(5) 应返回 15 但实际返回 10。运行它复现问题、"
                "定位并修复 bug(保持函数签名不变),然后验证 sum_to(5)==15、sum_to(1)==1、sum_to(10)==55",
        "check": check_bugfix,
    },
    {
        "id": "codebase-grep", "difficulty": "hard",
        "setup": setup_grep,
        "goal": "app/ 目录下有多个 Python 文件,找出所有包含 TODO 注释的文件,把文件路径逐行写入 "
                "todos.txt(相对路径,如 app/main.py),然后验证清单完整",
        "check": check_grep,
    },
]


def ablation_overrides(ablate: str) -> dict:
    """机制消融:把指定机制放宽到永不触发,用于对照实验。"""
    overrides: dict = {}
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
        else:
            raise SystemExit(f"未知消融项: {item}(可选 guard/retry/budget/validator)")
    return overrides


def _build_config(workdir: Path, overrides: dict, backend: str | None) -> Config:
    # 与 CLI 同源:优先加载 config/default.yaml(真实端点/模型名在此配置),再叠加跑批覆盖项
    default_cfg = PROJECT_ROOT / "config" / "default.yaml"
    cfg = Config.load(str(default_cfg)) if default_cfg.exists() else Config()
    cfg.set("workspace.root", str(workdir))
    cfg.set("checkpoint.root", str(workdir / ".checkpoints"))
    cfg.set("artifacts.root", str(workdir / ".artifacts"))
    cfg.set("orchestrator.planner_mode", "llm")
    cfg.set("orchestrator.max_rounds", MAX_TASK_ROUNDS)
    cfg.set("harness.max_steps", MAX_TASK_STEPS)
    # thinking 模型的规划/验证调用生成时间长,跑批超时放宽到 300s(Layer 7 实测教训)
    cfg.set("model.local_openai.timeout_seconds", 300)
    if backend:
        cfg.set("model.backend", backend)
    for key, value in overrides.items():
        cfg.set(key, value)
    return cfg


def run_one(task: dict, workdir: Path, overrides: dict, backend: str | None,
            model: str | None = None) -> dict:
    """跑单任务并返回指标行;工作区由调用方准备(setup 植入已在其中完成)。"""
    if model:
        overrides = {**overrides, "model.local_openai.model": model}
    events: list[dict] = []
    cfg = _build_config(workdir, overrides, backend)
    orch = Orchestrator(cfg, backend_factory=lambda t: create_backend(cfg),
                        on_event=events.append)
    start = time.time()
    report = orch.run(task["goal"])
    duration = time.time() - start
    # 客观检查器对准编排的共享交付工作区(子任务产物落在此处,而非 workdir 根)
    deliverable = Path(report.get("workspace") or workdir)
    check_ok, check_detail = task["check"](deliverable)

    return {
        "task": task["id"],
        "difficulty": task["difficulty"],
        "agent_success": report["success"],
        "check_passed": check_ok,
        "success": bool(report["success"] and check_ok),
        "check_detail": check_detail,
        "rounds": report["rounds"],
        "attempts": sum(t["attempts"] for t in report["subtasks"]),
        "tokens": sum(int(t.get("token_usage", 0)) for t in report["subtasks"]),
        "retries": sum(1 for e in events if e.get("type") == "task_retry_scheduled"),
        "replans": sum(1 for e in events if e.get("type") == "orchestration_replan"),
        "denied_actions": sum(1 for e in events
                              if e.get("type") == "tool_call" and e.get("status") == "denied"),
        "duration_s": round(duration, 1),
    }


def print_table(rows: list[dict], tag: str) -> None:
    print(f"=== Layer 7 结果 · {tag} ===")
    for r in rows:
        mark = "✅" if r["success"] else "❌"
        print(f" {mark} {r['task']:15s}({r['difficulty']:6s}) 轮数={r['rounds']} "
              f"尝试={r['attempts']} 拦截={r['denied_actions']} 重试={r['retries']} "
              f"tokens={r['tokens']} {r['duration_s']}s")
        if not r["success"]:
            print(f"    ✗ agent={r['agent_success']} check={r['check_passed']}"
                  f"({r['check_detail'][:80]})")
    ok = sum(1 for r in rows if r["success"])
    if rows:
        print(f"成功率 {ok}/{len(rows)} · 平均轮数 "
              f"{sum(r['rounds'] for r in rows) / len(rows):.1f} · "
              f"总 tokens {sum(r['tokens'] for r in rows)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentMuster Layer 7 多智能体基准")
    parser.add_argument("--suite", choices=["quick", "full"], default="full")
    parser.add_argument("--ablate", default="",
                        help="消融机制: guard,retry,budget,validator(逗号分隔)")
    parser.add_argument("--only", default=None, help="只跑指定任务 id(调试用)")
    parser.add_argument("--tag", default=None, help="结果目录标签(默认带时间戳)")
    parser.add_argument("--backend", choices=["mock", "local_openai"], default=None,
                        help="覆盖 model.backend(默认跟随 config/default.yaml)")
    parser.add_argument("--model", default=None,
                        help="覆盖 model.local_openai.model(如 qwen3:4b,调试/对照用)")
    args = parser.parse_args(argv)

    tasks = TASKS if args.suite == "full" else TASKS[:QUICK_COUNT]
    if args.only:
        tasks = [t for t in tasks if t["id"] == args.only]
        if not tasks:
            raise SystemExit(f"未找到任务: {args.only}(可选: {', '.join(t['id'] for t in TASKS)})")
    tag = args.tag or (f"layer7-{args.suite}"
                       + (f"-no-{args.ablate.replace(',', '-')}" if args.ablate else "")
                       + f"-{time.strftime('%m%d-%H%M')}")

    base_overrides = {
        "orchestrator.max_rounds": MAX_TASK_ROUNDS,
        "harness.max_steps": MAX_TASK_STEPS,
        **ablation_overrides(args.ablate),
    }
    rows = []
    for task in tasks:
        overrides = {**base_overrides, **task.get("overrides", {})}
        ts = time.strftime("%H%M%S")
        workdir = PROJECT_ROOT / "eval" / "workspaces" / f"{tag}-{task['id']}-{ts}"
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        if task.get("setup"):
            task["setup"](workdir)
        print(f"▶ 运行 {task['id']} ({task['difficulty']}) ...", flush=True)
        try:
            rows.append(run_one(task, workdir, overrides, args.backend, args.model))
            if args.model:
                rows[-1]["model"] = args.model
        except Exception as exc:
            rows.append({"task": task["id"], "difficulty": task["difficulty"],
                         "success": False, "agent_success": False, "check_passed": False,
                         "check_detail": f"{type(exc).__name__}: {exc}", "rounds": 0,
                         "attempts": 0, "tokens": 0, "retries": 0, "replans": 0,
                         "denied_actions": 0, "duration_s": 0})
        mark = "✅" if rows[-1]["success"] else "❌"
        print(f"  {mark} agent={rows[-1]['agent_success']} check={rows[-1]['check_passed']}",
              flush=True)

    result_dir = PROJECT_ROOT / "eval" / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    out_path = result_dir / f"{tag}.json"
    out_path.write_text(json.dumps({"tag": tag, "ablate": args.ablate, "rows": rows},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(rows, tag)
    print(f"结果已保存: {out_path}")
    return 0 if rows and all(r["success"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
