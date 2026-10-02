"""MCP(Model Context Protocol)stdio 客户端与工具代理(批次③,移植自 miniMaster)。

通过 JSON-RPC 2.0 over stdio 连接外部 MCP server:
initialize 握手 → tools/list 拉取工具清单 → 每个远程工具包装为 MCPProxyTool
(远程 inputSchema 直接作为 Tool.parameters,产出 OpenAI Function Call schema)
注册进 ToolRegistry——外部协议工具与内置工具走同一套安全链与 schema 出表。

读侧用后台线程 + 队列实现带超时的请求等待(Windows 管道不支持 select)。
"""
from __future__ import annotations

import atexit
import contextlib
import json
import queue
import shlex
import subprocess
import threading
from collections.abc import Callable
from typing import Any

from .base import WARN, Tool, ToolRegistry, ToolResult

MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    """MCP 通信或协议错误。"""


class MCPStdioClient:
    """一个 MCP server 进程的 stdio 连接(一个 client 对应一个 server)。"""

    def __init__(self, command: list[str], request_timeout: float = 30.0) -> None:
        self.command = command
        self.request_timeout = request_timeout
        self._proc: subprocess.Popen | None = None
        self._next_id = 1
        self._responses: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None
        self._send_lock = threading.Lock()

    # ---- 生命周期 ----
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
        if not isinstance(tools, list):
            raise MCPError("tools/list 返回格式异常")
        return tools

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    # ---- 请求 ----
    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list", {}).get("tools") or []

    def call_tool(self, name: str, arguments: dict) -> tuple[bool, str]:
        """调用远程工具,返回 (是否成功, 文本结果)。"""
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        ok = not result.get("isError")
        return ok, self._content_text(result)

    # ---- 内部 ----
    @staticmethod
    def _content_text(result: dict) -> str:
        parts = []
        for item in result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts) or json.dumps(result, ensure_ascii=False)

    def _request(self, method: str, params: dict) -> dict:
        if self._proc is None or self._proc.poll() is not None:
            raise MCPError("MCP server 未运行")
        with self._send_lock:
            req_id = self._next_id
            self._next_id += 1
            message = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            assert self._proc.stdin is not None
            self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        try:
            response = self._responses.get(timeout=self.request_timeout)
        except queue.Empty as exc:
            raise MCPError(f"MCP 请求超时(>{self.request_timeout}s): {method}") from exc
        if isinstance(response, MCPError):
            raise response
        if response.get("id") != req_id:
            raise MCPError(f"MCP 响应 id 不匹配: 期望 {req_id}")
        if "error" in response:
            raise MCPError(f"MCP 错误[{method}]: {response['error']}")
        return response.get("result") or {}

    def _notify(self, method: str, params: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._responses.put(message)
        self._responses.put(MCPError("MCP server 输出流已关闭"))


class MCPProxyTool(Tool):
    """把一个远程 MCP 工具包装为本地注册表工具。

    远程 inputSchema 即 Tool.parameters(同是 JSON Schema,零转换),经
    as_openai_schema() 直接产出 Function Call 协议;参数校验由 SafetyGuard
    统一执行。名称加 mcp_ 前缀避免与内置工具冲突;远程语义由 server 自治,
    本地按 WARN 标记(写类操作走 HITL 审批策略)。
    """

    def __init__(self, client: MCPStdioClient, tool_desc: dict[str, Any]) -> None:
        self._client = client
        self._remote_name = str(tool_desc.get("name", ""))
        self.name = f"mcp_{self._remote_name}"
        self.description = str(tool_desc.get("description")
                               or f"MCP 远程工具 {self._remote_name}")
        schema = tool_desc.get("inputSchema") or {"type": "object", "properties": {}}
        self.parameters = schema  # type: ignore[misc]
        self.danger = WARN

    def execute(self, ctx, **kwargs) -> ToolResult:
        del ctx  # 远程工具由 server 治理,本地沙箱不适用
        ok, text = self._client.call_tool(self._remote_name, kwargs)
        return ToolResult(ok=ok, output=text if ok else "",
                          error="" if ok else text)


def attach_mcp_tools(registry: ToolRegistry, server_cmd: str, timeout: float = 30.0,
                     on_event: Callable[[dict], None] | None = None) -> MCPStdioClient | None:
    """连接 MCP server 并把远程工具注册进 registry;失败降级为纯内置工具。

    返回 MCPStdioClient(进程生命周期经 atexit 兜底回收)或 None。
    """
    def emit(event_type: str, detail: dict) -> None:
        if on_event is not None:
            with contextlib.suppress(Exception):
                on_event({"type": event_type, **detail})

    if not server_cmd:
        return None
    try:
        client = MCPStdioClient(shlex.split(server_cmd), request_timeout=timeout)
        descs = client.start()
        if not descs:
            client.close()
            emit("mcp_unavailable", {"detail": "server 无工具"})
            return None
        for desc in descs:
            registry.register(MCPProxyTool(client, desc))
        atexit.register(client.close)
        emit("mcp_connected", {"server": server_cmd,
                               "tools": [d.get("name") for d in descs]})
        return client
    except Exception as exc:
        emit("mcp_unavailable", {"detail": f"{type(exc).__name__}: {exc}"})
        return None
