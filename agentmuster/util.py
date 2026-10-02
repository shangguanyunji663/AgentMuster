"""通用工具函数。

集中放置小但被多处复用的纯函数:哈希、原子写、时间戳、ID 生成。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path


def now_iso() -> str:
    """本地时间 ISO8601 字符串(精确到毫秒)。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + f".{int(time.time()*1000)%1000:03d}"


def short_id(prefix: str = "") -> str:
    """短 ID:前缀 + 8 位随机十六进制,便于人类阅读轨迹。"""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def sha256_text(text: str) -> str:
    """文本内容 SHA-256(用于文件摘要指纹与脱敏前一致性)。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    """文件内容 SHA-256。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在并返回其 Path。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


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


def json_dump(obj, path: str | Path, indent: int = 2, redactor=None) -> None:
    """序列化为 JSON 落盘;支持传入 redactor 做敏感信息脱敏。"""
    text = json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
    if redactor is not None:
        text = redactor.redact(text)
    atomic_write(path, text + "\n")


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
    """子进程标准环境:剥覆盖率调试钩子 + 强制 UTF-8 stdio。

    1) pytest-cov 以 --cov 运行时注入的 COV_CORE_* 会遗传给子进程,使其各自
       写出与主进程分支模式不一致的覆盖率数据,combine 时报 DataError(Linux
       CI 首跑实测);检查器脚本/MCP server/shell 命令都不在测量范围内。
    2) Windows CI 的子进程默认按 locale(cp1252)写 stdio,中文经 JSON 往返
       即成乱码;强制 PYTHONIOENCODING/PYTHONUTF8 统一为 UTF-8。
    """
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("COV_CORE_", "COVERAGE_")):
            env.pop(key)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def extract_json(text: str) -> dict:
    """从模型回复中尽力解析第一个合法 JSON 对象(裸 JSON / 代码块 / 首尾大括号兜底)。

    小模型常在 JSON 外包裹说明文字或 markdown 代码块;逐级尝试候选片段,
    全部失败抛 ValueError(由结构化输出助手回灌反馈重试)。
    """
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


def parse_text_action(content: str) -> dict | None:
    """从文本回复中提取动作:XML 工具标签 → 代码块 → 裸 JSON → 首尾大括号。

    返回 {"action": "tool", "name", "arguments"} 或 {"action": "final", "content"};
    无法解析返回 None(批次③,移植自 miniMaster 文本协议,快照 24f4247)。
    """
    if not content or not content.strip():
        return None
    # 部分模型在文本模式下仍用 XML 风格序列化工具调用(<tool_call>{...}</tool_call>)
    for tag in ("tool_call", "function_call"):
        for raw in re.findall(rf"<{tag}>\s*(\{{.*?\}})\s*</{tag}>", content, flags=re.S):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("name"):
                return {"action": "tool", "name": str(obj["name"]),
                        "arguments": obj.get("arguments") or {}}
    candidates = [content.strip()]
    fences = re.findall(r"```(?:json)?\s*(.*?)```", content, flags=re.S)
    candidates = [f.strip() for f in fences] + candidates
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("action") in ("tool", "final"):
            if obj["action"] == "tool" and not obj.get("name"):
                continue
            return obj
    return None
