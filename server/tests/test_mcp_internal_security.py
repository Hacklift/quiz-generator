import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMAIL_SENDER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("DB_NAME", "quizApp_test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")

from server.app.assistant.mcp_client import AssistantMcpClient
from server.app.core.config import Settings, settings
from server.app.mcp.middleware import McpAuthorizationHeaderMiddleware


def test_internal_mcp_url_defaults_to_port_env(monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    config = Settings()

    assert config.ASSISTANT_INTERNAL_MCP_URL == "http://127.0.0.1:10000/internal/mcp"


def test_assistant_mcp_client_sends_internal_secret(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_INTERNAL_MCP_SECRET", "internal-test-secret")
    client = AssistantMcpClient(mcp_url="http://127.0.0.1:8000/internal/mcp")

    assert client._internal_headers(None) == {
        "X-Internal-MCP-Token": "internal-test-secret",
    }
    assert client._internal_headers("Bearer user-token") == {
        "X-Internal-MCP-Token": "internal-test-secret",
        "Authorization": "Bearer user-token",
    }


@pytest.mark.asyncio
async def test_mcp_middleware_rejects_missing_internal_secret(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_INTERNAL_MCP_SECRET", "internal-test-secret")
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    middleware = McpAuthorizationHeaderMiddleware(app)
    sent_messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent_messages.append(message)

    await middleware(
        {"type": "http", "method": "POST", "path": "/internal/mcp", "headers": []},
        receive,
        send,
    )

    assert called is False
    assert sent_messages[0]["type"] == "http.response.start"
    assert sent_messages[0]["status"] == 403


@pytest.mark.asyncio
async def test_mcp_middleware_allows_valid_internal_secret(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_INTERNAL_MCP_SECRET", "internal-test-secret")
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = McpAuthorizationHeaderMiddleware(app)
    sent_messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent_messages.append(message)

    await middleware(
        {
            "type": "http",
            "method": "POST",
            "path": "/internal/mcp",
            "headers": [(b"x-internal-mcp-token", b"internal-test-secret")],
        },
        receive,
        send,
    )

    assert called is True
    assert sent_messages[0]["status"] == 200
