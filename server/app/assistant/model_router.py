import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from server.app.assistant.providers import (
    AssistantModelProvider,
    AssistantProviderError,
    GeminiProvider,
    GroqProvider,
)
from server.app.assistant.schemas import AssistantFinalResponse, ExecutorDecision, PlannerDecision
from server.app.core.config import settings


logger = logging.getLogger(__name__)
TModel = TypeVar("TModel", bound=BaseModel)


class AssistantModelRouter:
    def __init__(self):
        self._planner_provider = self._build_provider(
            settings.ASSISTANT_PLANNER_PROVIDER,
        )
        self._executor_provider = self._build_provider(
            settings.ASSISTANT_EXECUTOR_PROVIDER,
        )

    def _build_provider(self, provider_name: str) -> AssistantModelProvider:
        normalized = provider_name.lower().strip()
        if normalized == "gemini":
            return GeminiProvider(settings.GEMINI_API_KEY)
        if normalized == "groq":
            return GroqProvider(settings.GROQ_API_KEY)
        raise AssistantProviderError(f"Unsupported assistant provider: {provider_name}")

    async def plan(self, prompt: str) -> PlannerDecision:
        return await self._generate_validated(
            provider=self._planner_provider,
            primary_model=settings.ASSISTANT_PLANNER_MODEL,
            fallback_model=settings.ASSISTANT_PLANNER_FALLBACK_MODEL,
            prompt=prompt,
            response_model=PlannerDecision,
            role_name="planner",
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        return await self._generate_validated(
            provider=self._executor_provider,
            primary_model=settings.ASSISTANT_EXECUTOR_MODEL,
            fallback_model=settings.ASSISTANT_EXECUTOR_FALLBACK_MODEL,
            prompt=prompt,
            response_model=ExecutorDecision,
            role_name="executor",
        )

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        return await self._generate_validated(
            provider=self._planner_provider,
            primary_model=settings.ASSISTANT_PLANNER_MODEL,
            fallback_model=settings.ASSISTANT_PLANNER_FALLBACK_MODEL,
            prompt=prompt,
            response_model=AssistantFinalResponse,
            role_name="final_response",
        )

    async def _generate_validated(
        self,
        *,
        provider: AssistantModelProvider,
        primary_model: str,
        fallback_model: str,
        prompt: str,
        response_model: type[TModel],
        role_name: str,
    ) -> TModel:
        last_error: Exception | None = None
        for model in (primary_model, primary_model, fallback_model):
            try:
                raw_response = await provider.generate(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Return only valid JSON in message content.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )
                return self._parse_json_model(raw_response, response_model)
            except (AssistantProviderError, ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning("%s model %s failed validation/request: %s", role_name, model, exc)
                continue

        raise AssistantProviderError(f"{role_name} model failed after retry and fallback: {last_error}")

    def _parse_json_model(self, raw_response: str, response_model: type[TModel]) -> TModel:
        payload = _strip_json_payload(raw_response)
        data = _loads_json_lenient(payload)
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        return response_model.model_validate(data)


def _strip_json_payload(raw_response: str) -> str:
    payload = raw_response.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        payload = "\n".join(lines).strip()
    return payload


def _loads_json_lenient(payload: str) -> object:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        extracted = _extract_json_container(payload)
        if extracted and extracted != payload:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                payload = extracted
        repaired = re.sub(r",(\s*[}\]])", r"\1", payload)
        return json.loads(repaired)


def _extract_json_container(payload: str) -> str | None:
    starts = [index for index in (payload.find("{"), payload.find("[")) if index >= 0]
    if not starts:
        return None
    start = min(starts)
    opening = payload[start]
    closing = "}" if opening == "{" else "]"
    end = payload.rfind(closing)
    if end <= start:
        return None
    return payload[start : end + 1].strip()
