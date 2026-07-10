from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from server.app.assistant.schemas import PlanStep, ToolResult
from server.app.core.config import settings
from server.app.db.core.redis import get_redis_client


@dataclass
class PendingAssistantRun:
    run_id: str
    user_id: str | None
    conversation_id: str
    message: str
    plan: list[PlanStep]
    current_step_index: int
    tool_results: list[ToolResult] = field(default_factory=list)
    page_context: dict[str, Any] | None = None
    recent_artifacts: list[dict[str, Any]] | None = None
    pending_mode: str | None = None
    missing_arguments: list[str] = field(default_factory=list)

    def model_dump(self) -> dict:
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "message": self.message,
            "plan": [step.model_dump(mode="json") for step in self.plan],
            "current_step_index": self.current_step_index,
            "tool_results": [result.model_dump(mode="json") for result in self.tool_results],
            "page_context": self.page_context,
            "recent_artifacts": self.recent_artifacts,
            "pending_mode": self.pending_mode,
            "missing_arguments": self.missing_arguments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PendingAssistantRun":
        return cls(
            run_id=data["run_id"],
            user_id=data.get("user_id"),
            conversation_id=data["conversation_id"],
            message=data["message"],
            plan=[PlanStep(**step) for step in data.get("plan", [])],
            current_step_index=int(data.get("current_step_index", 0)),
            tool_results=[ToolResult(**result) for result in data.get("tool_results", [])],
            page_context=data.get("page_context"),
            recent_artifacts=data.get("recent_artifacts"),
            pending_mode=data.get("pending_mode"),
            missing_arguments=list(data.get("missing_arguments", [])),
        )


class AssistantRunStore(Protocol):
    async def save(self, pending_run: PendingAssistantRun) -> None:
        ...

    async def pop(
        self,
        *,
        run_id: str,
        user_id: str | None,
        conversation_id: str,
    ) -> PendingAssistantRun | None:
        ...

    async def pop_for_conversation(
        self,
        *,
        user_id: str | None,
        conversation_id: str,
        pending_mode: str,
    ) -> PendingAssistantRun | None:
        ...


class RedisAssistantRunStore:
    def __init__(self, *, ttl_seconds: int | None = None):
        self.ttl_seconds = ttl_seconds or settings.ASSISTANT_PENDING_RUN_TTL_SECONDS

    @staticmethod
    def _key(run_id: str) -> str:
        return f"assistant:pending_run:{run_id}"

    @staticmethod
    def _conversation_key(user_id: str | None, conversation_id: str, pending_mode: str) -> str:
        return f"assistant:pending_run:{pending_mode}:{user_id or 'anonymous'}:{conversation_id}"

    async def save(self, pending_run: PendingAssistantRun) -> None:
        redis_client = await get_redis_client()
        await redis_client.setex(
            self._key(pending_run.run_id),
            self.ttl_seconds,
            json.dumps(pending_run.model_dump(), default=str),
        )
        if pending_run.pending_mode:
            await redis_client.setex(
                self._conversation_key(
                    pending_run.user_id,
                    pending_run.conversation_id,
                    pending_run.pending_mode,
                ),
                self.ttl_seconds,
                pending_run.run_id,
            )

    async def pop(
        self,
        *,
        run_id: str,
        user_id: str | None,
        conversation_id: str,
    ) -> PendingAssistantRun | None:
        redis_client = await get_redis_client()
        key = self._key(run_id)
        raw = await redis_client.get(key)
        if not raw:
            return None
        await redis_client.delete(key)
        pending_run = PendingAssistantRun.from_dict(json.loads(raw))
        if pending_run.user_id != user_id or pending_run.conversation_id != conversation_id:
            return None
        return pending_run

    async def pop_for_conversation(
        self,
        *,
        user_id: str | None,
        conversation_id: str,
        pending_mode: str,
    ) -> PendingAssistantRun | None:
        redis_client = await get_redis_client()
        conversation_key = self._conversation_key(user_id, conversation_id, pending_mode)
        run_id = await redis_client.get(conversation_key)
        if not run_id:
            return None
        if isinstance(run_id, bytes):
            run_id = run_id.decode()
        await redis_client.delete(conversation_key)
        return await self.pop(
            run_id=str(run_id),
            user_id=user_id,
            conversation_id=conversation_id,
        )


class InMemoryAssistantRunStore:
    def __init__(self):
        self._runs: dict[str, PendingAssistantRun] = {}

    async def save(self, pending_run: PendingAssistantRun) -> None:
        self._runs[pending_run.run_id] = pending_run

    async def pop(
        self,
        *,
        run_id: str,
        user_id: str | None,
        conversation_id: str,
    ) -> PendingAssistantRun | None:
        pending_run = self._runs.pop(run_id, None)
        if pending_run is None:
            return None
        if pending_run.user_id != user_id or pending_run.conversation_id != conversation_id:
            return None
        return pending_run

    async def pop_for_conversation(
        self,
        *,
        user_id: str | None,
        conversation_id: str,
        pending_mode: str,
    ) -> PendingAssistantRun | None:
        for run_id, pending_run in list(self._runs.items()):
            if (
                pending_run.user_id == user_id
                and pending_run.conversation_id == conversation_id
                and pending_run.pending_mode == pending_mode
            ):
                return self._runs.pop(run_id)
        return None
