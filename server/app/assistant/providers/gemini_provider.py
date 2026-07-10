import asyncio

from server.app.assistant.providers.base import (
    AssistantModelProvider,
    AssistantProviderError,
    normalize_messages,
    require_api_key,
)


class GeminiProvider(AssistantModelProvider):
    def __init__(self, api_key: str | None):
        self.api_key = require_api_key(api_key, "Gemini")

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0,
    ) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AssistantProviderError(
                "google-genai is not installed. Run `pipenv install google-genai` in server/."
            ) from exc

        normalized = normalize_messages(messages)
        prompt = "\n\n".join(f"{item['role']}: {item['content']}" for item in normalized)

        def _call() -> str:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""

        try:
            return await asyncio.to_thread(_call)
        except Exception as exc:
            raise AssistantProviderError(f"Gemini request failed: {exc}") from exc
