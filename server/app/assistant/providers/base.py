from abc import ABC, abstractmethod
from typing import Any


class AssistantProviderError(RuntimeError):
    pass


class AssistantModelProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0,
    ) -> str:
        raise NotImplementedError


def require_api_key(api_key: str | None, provider_name: str) -> str:
    if not api_key:
        raise AssistantProviderError(f"{provider_name} API key is not configured.")
    return api_key


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": str(message.get("role", "user")),
            "content": str(message.get("content", "")),
        }
        for message in messages
    ]
