"""LocalOpenAIBackend 协议降级/文本动作解析/截断自愈测试(本地 HTTP 桩,批次③)。

miniMaster 同层(llm/client.py)覆盖率仅约 32%,是移植时明确要修复的测试盲区
(MERGE_DESIGN 默认项 2);本文件用真实 HTTP 桩补齐协议状态机的行为级单测。
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agentmuster.models.local_openai import LocalOpenAIBackend

TOOLS = [{"type": "function", "function": {"name": "file_read",
          "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                         "required": ["path"]}}}]


def _resp(body: dict, status: int = 200):
    return status, body


def _choice(content: str = "", tool_calls=None, finish: str = "stop"):
    msg: dict = {"content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"choices": [{"message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


@pytest.fixture
def server():
    received: list[dict] = []
    plan: list = []  # 每项:(status, body) 或 callable(body) -> (status, body)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n))
            received.append(body)
            item = plan.pop(0)
            status, payload = item(body) if callable(item) else item
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    httpd = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd, received, plan
    httpd.shutdown()


def _backend(server) -> LocalOpenAIBackend:
    httpd, _, _ = server
    return LocalOpenAIBackend(base_url=f"http://127.0.0.1:{httpd.server_port}/v1",
                              api_key="test", model="stub", timeout_seconds=10,
                              max_retries=0, max_tokens=100)


def test_native_tool_calls_passthrough(server):
    _, received, plan = server
    plan.append(_resp(_choice(tool_calls=[{"id": "c1",
                "function": {"name": "file_read", "arguments": "{\"path\": \"a.txt\"}"}}],
                finish="tool_calls")))
    backend = _backend(server)
    resp = backend.complete([{"role": "user", "content": "hi"}], tools=TOOLS)
    assert resp.tool_calls[0]["name"] == "file_read"
    assert backend.protocol_mode == "native"
    assert "tools" in received[0]


def test_downgrade_on_400_then_text_action(server):
    _, received, plan = server
    plan.append((400, {"error": {"message": "tools not supported"}}))
    plan.append(_resp(_choice(content='{"action": "tool", "name": "file_read", '
                              '"arguments": {"path": "a.txt"}}')))
    backend = _backend(server)
    resp = backend.complete([{"role": "user", "content": "hi"}], tools=TOOLS)
    assert backend.protocol_mode == "text_json"     # 单向降级
    assert resp.tool_calls[0]["name"] == "file_read"
    assert "tools" not in received[1]               # 降级后 payload 不带 tools
    assert "工具调用协议" in received[1]["messages"][0]["content"]  # 目录注入 system


def test_text_action_parsed_without_downgrade(server):
    _, _, plan = server
    plan.append(_resp(_choice(content='```json\n{"action": "tool", "name": "file_read", '
                              '"arguments": {"path": "a.txt"}}\n```')))
    backend = _backend(server)
    resp = backend.complete([{"role": "user", "content": "hi"}], tools=TOOLS)
    assert backend.protocol_mode == "native"        # 文本可解析,不触发降级
    assert resp.tool_calls[0]["name"] == "file_read"


def test_final_action_becomes_content(server):
    _, _, plan = server
    plan.append(_resp(_choice(content='{"action": "final", "content": "做完了"}')))
    backend = _backend(server)
    resp = backend.complete([{"role": "user", "content": "hi"}], tools=TOOLS)
    assert resp.content == "做完了" and not resp.tool_calls


def test_truncation_self_heal_doubles_max_tokens(server):
    _, received, plan = server

    def first(body):
        assert body["max_tokens"] == 100
        return _resp(_choice(content="部分", finish="length"))

    def second(body):
        assert body["max_tokens"] == 200
        return _resp(_choice(content="完整回复", finish="stop"))

    plan += [first, second]
    backend = _backend(server)
    resp = backend.complete([{"role": "user", "content": "hi"}])
    assert resp.content == "完整回复" and resp.finish_reason == "stop"
    assert received[1]["max_tokens"] == 200         # 截断自愈:翻倍重试一次


def test_no_fallback_when_disabled(server):
    _, _, plan = server
    plan.append((400, {"error": {"message": "tools not supported"}}))
    backend = _backend(server)
    backend.protocol_fallback = False
    with pytest.raises(ConnectionError):
        backend.complete([{"role": "user", "content": "hi"}], tools=TOOLS)
