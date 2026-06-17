from server.app.assistant.providers.base import (
    AssistantModelProvider,
    AssistantProviderError,
    normalize_messages,
    require_api_key,
)


class GroqProvider(AssistantModelProvider):
    def __init__(self, api_key: str | None):
        self.api_key = require_api_key(api_key, "Groq")

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0,
    ) -> str:
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise AssistantProviderError(
                "groq is not installed. Run `pipenv install groq` in server/."
            ) from exc

        client = AsyncGroq(api_key=self.api_key)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=normalize_messages(messages),
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise AssistantProviderError(f"Groq request failed: {exc}") from exc
