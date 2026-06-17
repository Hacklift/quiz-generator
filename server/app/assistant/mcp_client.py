import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from server.app.core.config import settings


class AssistantMcpClient:
    def __init__(self, *, mcp_url: str | None = None):
        self.mcp_url = mcp_url or settings.ASSISTANT_INTERNAL_MCP_URL

    async def call_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        authorization_header: str | None = None,
    ) -> Any:
        headers = self._internal_headers(authorization_header)

        async with streamablehttp_client(self.mcp_url, headers=headers) as (
            read_stream,
            write_stream,
            _get_session_id,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self._normalize_result(result)

    def _internal_headers(self, authorization_header: str | None) -> dict[str, str]:
        headers = {
            "X-Internal-MCP-Token": settings.resolved_assistant_internal_mcp_secret,
        }
        if authorization_header:
            headers["Authorization"] = authorization_header
        return headers

    def _normalize_result(self, result: Any) -> Any:
        is_error = bool(getattr(result, "isError", False))
        structured_content = getattr(result, "structuredContent", None)
        if structured_content is not None:
            if is_error and isinstance(structured_content, dict):
                return {"isError": True, **structured_content}
            return structured_content

        content = getattr(result, "content", None) or []
        normalized_items = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                try:
                    normalized_items.append(json.loads(text))
                except json.JSONDecodeError:
                    normalized_items.append(text)
                continue
            normalized_items.append(item.model_dump(mode="json") if hasattr(item, "model_dump") else item)

        if len(normalized_items) == 1:
            payload = normalized_items[0]
        else:
            payload = normalized_items

        if is_error:
            return {"isError": True, "error": payload}
        return payload
