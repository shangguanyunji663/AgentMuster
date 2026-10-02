"""CI 覆盖率门禁:全局 ≥75%,多智能体编排层 ≥90%(批次⑤)。

pytest-cov 不支持按路径分别 fail_under,故以 coverage.json + 本脚本断言:

    pytest --cov=agentmuster --cov-report=json:coverage.json
    python scripts/check_coverage.py coverage.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GLOBAL_FLOOR = 75.0
ORCHESTRATOR_FLOOR = 90.0


def _is_orchestrator(path: str) -> bool:
    p = path.replace("\\", "/")
    return p.startswith("agentmuster/orchestrator/") or p == "agentmuster/agent/orchestrator.py"


def main(argv: list[str] | None = None) -> int:
    report = argv[0] if argv else "coverage.json"
    data = json.loads(Path(report).read_text(encoding="utf-8"))
    total = float(data["totals"]["percent_covered"])
    orch_files = {f: v for f, v in data["files"].items() if _is_orchestrator(f)}
    covered = sum(v["summary"]["covered_lines"] for v in orch_files.values())
    statements = sum(v["summary"]["num_statements"] for v in orch_files.values())
    orch = covered / statements * 100 if statements else 100.0

    ok = True
    if total < GLOBAL_FLOOR:
        print(f"[FAIL] 全局覆盖率 {total:.1f}% < {GLOBAL_FLOOR}%")
        ok = False
    else:
        print(f"[OK] 全局覆盖率 {total:.1f}% >= {GLOBAL_FLOOR}%")
    if orch < ORCHESTRATOR_FLOOR:
        print(f"[FAIL] 编排层覆盖率 {orch:.1f}% < {ORCHESTRATOR_FLOOR}%")
        ok = False
    else:
        # 输出只用 ASCII:Windows runner 控制台 cp1252 打不出 ✓/✗(首跑实测)
        print(f"[OK] 编排层覆盖率 {orch:.1f}% >= {ORCHESTRATOR_FLOOR}%"
              f"({covered}/{statements} 行,{len(orch_files)} 文件)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
