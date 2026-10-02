"""MCP stdio 客户端与代理工具测试(本地 fake server,真实子进程+管道;移植自 miniMaster)。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agentmuster.safety import validate_params
from agentmuster.tools import ToolRegistry
from agentmuster.tools.base import ToolContext
from agentmuster.tools.mcp_client import MCPError, MCPProxyTool, MCPStdioClient

SERVER = Path(__file__).parent / "mcp_fake_server.py"


@pytest.fixture()
def client():
    client = MCPStdioClient([sys.executable, str(SERVER)], request_timeout=15)
    yield client
    client.close()


def test_start_handshake_and_list_tools(client):
    tools = client.start()
    assert [t["name"] for t in tools] == ["add", "echo"]
    assert tools[0]["inputSchema"]["required"] == ["a", "b"]


def test_call_tool_roundtrip(client):
    client.start()
    ok, text = client.call_tool("add", {"a": 2, "b": 3})
    assert ok and text == "5"
    ok, text = client.call_tool("echo", {"text": "你好 mcp"})
    assert ok and text == "你好 mcp"


def test_call_unknown_tool_is_error(client):
    client.start()
    ok, _ = client.call_tool("nope", {})
    assert not ok


def test_proxy_tool_through_registry(client):
    client.start()
    registry = ToolRegistry()
    for desc in client.list_tools():
        registry.register(MCPProxyTool(client, desc))

    # mcp_ 前缀避免与内置工具冲突;schema 直接来自远端 inputSchema
    assert registry.has("mcp_add") and registry.has("mcp_echo")
    schema = registry.get("mcp_add").as_openai_schema()
    assert schema["parameters"]["required"] == ["a", "b"]

    out = registry.get("mcp_add").execute(ToolContext(), a=20, b=22)
    assert out.ok and out.output == "42"
    out = registry.get("mcp_echo").execute(ToolContext(), text="你好")
    assert out.ok and out.output == "你好"


def test_proxy_schema_validation_guards_params(client):
    # 缺参数 → SafetyGuard 的参数校验拦截(远端 schema 即本地校验依据)
    client.start()
    registry = ToolRegistry()
    registry.register(MCPProxyTool(client, client.list_tools()[0]))
    tool = registry.get("mcp_add")
    errors = validate_params(tool.parameters, {"a": 1})
    assert any("缺少必填参数" in e for e in errors)


def test_server_crash_raises_mcp_error():
    client = MCPStdioClient([sys.executable, "-c", "import sys; sys.exit(1)"])
    with pytest.raises(MCPError):
        client.start()
