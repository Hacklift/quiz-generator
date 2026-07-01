from __future__ import annotations

import re
from typing import Any

from server.app.assistant.resource_resolver import AssistantResourceResolver, ResolvedQuizResource
from server.app.assistant.schemas import PlanStep


SAVE_INTENT_PATTERN = re.compile(r"\b(save|store|keep|add\s+to\s+(?:my\s+)?library)\b", re.IGNORECASE)
DOWNLOAD_INTENT_PATTERN = re.compile(r"\b(download|export)\b", re.IGNORECASE)


class AssistantPlanCompiler:
    def __init__(self, *, resolver: AssistantResourceResolver | None = None):
        self.resolver = resolver or AssistantResourceResolver()

    def compile(
        self,
        *,
        steps: list[PlanStep],
        message: str,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> list[PlanStep]:
        resolved_quiz = self.resolver.resolve_quiz(
            message=message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        if resolved_quiz is None:
            return steps

        compiled_steps = [step.model_copy(deep=True) for step in steps]
        compiled_steps = self._hydrate_quiz_arguments(compiled_steps, resolved_quiz)
        compiled_steps = self._add_artifact_save_step_if_missing(compiled_steps, message, resolved_quiz)
        compiled_steps = self._add_artifact_download_step_if_missing(compiled_steps, message, resolved_quiz)
        return compiled_steps

    def _hydrate_quiz_arguments(
        self,
        steps: list[PlanStep],
        resolved_quiz: ResolvedQuizResource,
    ) -> list[PlanStep]:
        for step in steps:
            if step.tool_name in {
                "library_save_quiz",
                "quiz_export_link",
                "quiz_get_answers",
                "share_create_link",
                "share_send_email",
                "live_quiz_get_access_link",
                "live_quiz_create_access_link",
                "live_quiz_ensure_access_link",
                "live_quiz_send_invites",
            }:
                if resolved_quiz.quiz_id and not _has_value(step.arguments.get("quiz_id")):
                    step.arguments["quiz_id"] = resolved_quiz.quiz_id
                if step.tool_name == "library_save_quiz":
                    step.arguments.setdefault("title", resolved_quiz.title)
                    if resolved_quiz.question_type:
                        step.arguments.setdefault("question_type", resolved_quiz.question_type)
            if step.tool_name == "library_get_history_detail" and resolved_quiz.history_id:
                step.arguments.setdefault("history_id", resolved_quiz.history_id)
            if step.tool_name == "library_get_saved_quiz" and resolved_quiz.saved_quiz_id:
                step.arguments.setdefault("saved_quiz_id", resolved_quiz.saved_quiz_id)
        return steps

    def _add_artifact_save_step_if_missing(
        self,
        steps: list[PlanStep],
        message: str,
        resolved_quiz: ResolvedQuizResource,
    ) -> list[PlanStep]:
        if not SAVE_INTENT_PATTERN.search(message):
            return steps
        if any(step.tool_name == "library_save_quiz" for step in steps):
            return steps
        if not resolved_quiz.quiz_id:
            return steps
        steps.append(
            PlanStep(
                step_id=_next_step_id(steps),
                tool_name="library_save_quiz",
                arguments={
                    "quiz_id": resolved_quiz.quiz_id,
                    "title": resolved_quiz.title,
                    **({"question_type": resolved_quiz.question_type} if resolved_quiz.question_type else {}),
                },
                requires_confirmation=True,
                reason="Save the quiz selected from recent assistant artifacts.",
            )
        )
        return steps

    def _add_artifact_download_step_if_missing(
        self,
        steps: list[PlanStep],
        message: str,
        resolved_quiz: ResolvedQuizResource,
    ) -> list[PlanStep]:
        if not DOWNLOAD_INTENT_PATTERN.search(message):
            return steps
        if any(step.tool_name == "quiz_export_link" for step in steps):
            return steps
        if not resolved_quiz.quiz_id:
            return steps
        depends_on = [steps[-1].step_id] if steps and steps[-1].tool_name == "library_save_quiz" else []
        steps.append(
            PlanStep(
                step_id=_next_step_id(steps),
                tool_name="quiz_export_link",
                arguments={"quiz_id": resolved_quiz.quiz_id},
                depends_on=depends_on,
                reason="Prepare the requested download for the selected quiz.",
            )
        )
        return steps


def _next_step_id(steps: list[PlanStep]) -> str:
    existing_ids = {step.step_id for step in steps}
    index = len(existing_ids) + 1
    while f"step_{index}" in existing_ids:
        index += 1
    return f"step_{index}"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True
