from __future__ import annotations

import re
from typing import Any

from server.app.assistant.confirmation_presenter import find_title_for_id
from server.app.assistant.resource_resolver import AssistantResourceResolver, ResolvedQuizResource
from server.app.assistant.schemas import PlanStep, PlannerDecision


SAVE_INTENT_PATTERN = re.compile(r"\b(save|store|keep|add\s+to\s+(?:my\s+)?library)\b", re.IGNORECASE)
DOWNLOAD_INTENT_PATTERN = re.compile(r"\b(download|export)\b", re.IGNORECASE)
QUIZ_NOUN_PATTERN = r"(?:quiz(?:zes|ze)?|questions?|tests?|assessments?)"
GENERATION_VERBS_PATTERN = r"(?:generate|create|make|build|produce|draft|set up)"
GENERATION_INTENT_PATTERN = re.compile(
    rf"\b{GENERATION_VERBS_PATTERN}\b.*\b{QUIZ_NOUN_PATTERN}\b"
    rf"|\b{QUIZ_NOUN_PATTERN}\b.*\b{GENERATION_VERBS_PATTERN}\b",
    re.IGNORECASE,
)
QUESTION_TYPE_PATTERNS = (
    (re.compile(r"\b(multiple[-\s]*choice|multi[-\s]*choice|multichoice|mcq)\b", re.IGNORECASE), "multichoice"),
    (re.compile(r"\b(true[-\s]*/?[-\s]*false|true\s+or\s+false)\b", re.IGNORECASE), "true-false"),
    (re.compile(r"\b(open[-\s]*ended|essay)\b", re.IGNORECASE), "open-ended"),
    (re.compile(r"\b(short[-\s]*answer)\b", re.IGNORECASE), "short-answer"),
)
EXPORT_FORMAT_PATTERNS = (
    (re.compile(r"\bpdf\b", re.IGNORECASE), "pdf"),
    (re.compile(r"\bdocx\b|\bword\s+document\b", re.IGNORECASE), "docx"),
    (re.compile(r"\btxt\b|\btext\s+file\b", re.IGNORECASE), "txt"),
    (re.compile(r"\bjson\b", re.IGNORECASE), "json"),
)
CANONICAL_ID_PATTERN = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)
LIVE_QUIZ_LINK_INTENT_PATTERN = re.compile(
    r"\blive\s+quiz\b.*\b(link|access\s+code|attempt\s+link|participant\s+link|invite)\b"
    r"|\b(link|access\s+code|attempt\s+link|participant\s+link|invite)\b.*\blive\s+quiz\b"
    r"|\blive\s+(?:link|access\s+link|attempt\s+link|participant\s+link)\b.*\bquiz\b"
    r"|\bquiz\b.*\blive\s+(?:link|access\s+link|attempt\s+link|participant\s+link)\b",
    re.IGNORECASE,
)
LIVE_QUIZ_LINK_ONLY_CREATION_PATTERN = re.compile(
    rf"\b{GENERATION_VERBS_PATTERN}\b\s+(?:a|an|the|new|valid|active)?\s*"
    r"(?:live\s+)?(?:quiz\s+)?(?:link|access\s+code|attempt\s+link|participant\s+link|invite)\b"
    rf"|\b{GENERATION_VERBS_PATTERN}\b\s+(?:a|an|the|new|valid|active)?\s*live\s+quiz\s+"
    r"(?:link|access\s+code|attempt\s+link|participant\s+link|invite)\b",
    re.IGNORECASE,
)
LIVE_QUIZ_CREATE_INTENT_PATTERN = re.compile(r"\b(create|generate|make|build|set\s+up|new|regenerate|replace)\b", re.IGNORECASE)
EMAIL_ADDRESS_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
LIVE_QUIZ_DURATION_VALUE_PATTERNS = (
    re.compile(r"\b(?:duration|quiz\s+duration)\b\D{0,30}(\d+)\s*(minutes?|mins?|hours?|hrs?)?\b", re.IGNORECASE),
    re.compile(r"\b(?:use|set|make|give)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+(?:as\s+)?(?:the\s+)?(?:quiz\s+)?duration\b", re.IGNORECASE),
    re.compile(r"\b(?:use|set|make|give)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", re.IGNORECASE),
    re.compile(r"\bfor\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", re.IGNORECASE),
    re.compile(r"\bwith\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+(?:quiz\s+)?duration\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*[- ]?(minute|min|hour|hr)\s+(?:quiz|live\s+quiz|duration)\b", re.IGNORECASE),
    re.compile(r"^\s*(\d+)\s*(minutes?|mins?|hours?|hrs?)\s*[.?!]?\s*$", re.IGNORECASE),
)
FOLDER_ADD_INTENT_PATTERN = re.compile(
    r"\b(add|save|put|place|move)\b.*\bfolder\b|\bfolder\b.*\b(add|save|put|place|move)\b",
    re.IGNORECASE,
)
FOLDER_NAME_PATTERN = re.compile(
    r"\b(?:to|in|into)\s+(?:my|the|a|an)?\s*([A-Za-z0-9][A-Za-z0-9 &_-]*?)\s+folder\b",
    re.IGNORECASE,
)
LIVE_QUIZ_TOOLS = {
    "live_quiz_get_access_link",
    "live_quiz_create_access_link",
    "live_quiz_ensure_access_link",
    "live_quiz_send_invites",
}


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
    def harden(
        self,
        planner: PlannerDecision,
        message: str,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> PlannerDecision:
        planner.steps = self._normalize_question_type_arguments(planner.steps)
        planner.steps = self._normalize_export_formats(planner.steps, message)
        planner.steps = self._normalize_live_quiz_duration(planner.steps, message)
        planner.steps = self._normalize_live_quiz_ensure_workflow(planner.steps, message)
        planner.steps = self.normalize_live_quiz_identity(
            planner.steps,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        planner.steps = self.compile(
            steps=planner.steps,
            message=message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        planner.steps = self._complete_generated_quiz_workflow(planner.steps, message)
        planner.needs_tools = bool(planner.steps)
        return planner

    def _normalize_question_type_arguments(self, steps: list[PlanStep]) -> list[PlanStep]:
        for step in steps:
            question_type = step.arguments.get("question_type")
            if not isinstance(question_type, str):
                continue
            normalized = self._canonical_question_type_from_text(question_type)
            if normalized is not None:
                step.arguments["question_type"] = normalized
        return steps

    def _normalize_live_quiz_ensure_workflow(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        tool_names = {step.tool_name for step in steps}
        wants_conditional_create = bool(
            LIVE_QUIZ_LINK_INTENT_PATTERN.search(message)
            and re.search(r"\b(if\s+not|otherwise|create\s+(?:one|it|a\s+link)|send|email|invite)\b", message, re.IGNORECASE)
        )
        if not wants_conditional_create and "live_quiz_send_invites" not in tool_names:
            return steps

        ensure_step: PlanStep | None = None
        normalized_steps: list[PlanStep] = []
        for step in steps:
            if step.tool_name in {"live_quiz_get_access_link", "live_quiz_create_access_link"}:
                if ensure_step is None:
                    ensure_step = PlanStep(
                        step_id=step.step_id,
                        tool_name="live_quiz_ensure_access_link",
                        arguments=dict(step.arguments),
                        requires_confirmation=False,
                        depends_on=list(step.depends_on),
                        reason=step.reason,
                    )
                    normalized_steps.append(ensure_step)
                continue
            normalized_steps.append(step)

        if ensure_step is None:
            return steps

        for step in normalized_steps:
            if step.tool_name != "live_quiz_send_invites":
                continue
            if "live_quiz_link" not in step.arguments:
                step.arguments["live_quiz_link"] = f"$steps.{ensure_step.step_id}.result.live_quiz_link"
            if ensure_step.step_id not in step.depends_on:
                step.depends_on = [*step.depends_on, ensure_step.step_id]

        return normalized_steps

    def missing_explicit_workflow_intents(self, steps: list[PlanStep], message: str) -> list[str]:
        tool_names = {step.tool_name for step in steps}
        missing: list[str] = []
        if self._message_explicitly_requests_generation(message) and "quiz_generate" not in tool_names:
            missing.append("generate_quiz")
        if DOWNLOAD_INTENT_PATTERN.search(message) and "quiz_export_link" not in tool_names:
            missing.append("download_quiz")
        if LIVE_QUIZ_LINK_INTENT_PATTERN.search(message) and not (tool_names & LIVE_QUIZ_TOOLS):
            if LIVE_QUIZ_CREATE_INTENT_PATTERN.search(message):
                missing.append("create_live_quiz_link")
            else:
                missing.append("get_live_quiz_link")

        folder_name = self._folder_name_from_message(message)
        wants_folder_add = bool(folder_name and FOLDER_ADD_INTENT_PATTERN.search(message))
        if wants_folder_add and "folder_add_saved_quiz" not in tool_names:
            missing.append("add_quiz_to_folder")
        return missing

    def plan_clarification_message(self, missing_intents: list[str]) -> str:
        readable = {
            "generate_quiz": "generate the quiz",
            "download_quiz": "prepare the download",
            "add_quiz_to_folder": "add the quiz to the folder",
            "create_live_quiz_link": "create the live quiz link",
            "get_live_quiz_link": "check the live quiz link",
        }
        missing = ", ".join(readable.get(intent, intent) for intent in missing_intents)
        return f"I need a bit more detail before I can {missing}. Please restate the request with the quiz and target details."

    def _normalize_export_formats(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        requested_format = self._explicit_export_format_from_message(message)
        allow_context_format = bool(re.search(r"\b(same|previous|again)\s+format\b", message, re.IGNORECASE))
        for step in steps:
            if step.tool_name != "quiz_export_link":
                continue
            if requested_format:
                step.arguments["format"] = requested_format
            elif not allow_context_format:
                step.arguments.pop("format", None)
        return steps

    def _complete_generated_quiz_workflow(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        generate_step = self._first_step_with_tool(steps, "quiz_generate")
        if generate_step is None:
            return steps

        completed_steps = list(steps)
        folder_name = self._folder_name_from_message(message)
        wants_folder_add = bool(folder_name and FOLDER_ADD_INTENT_PATTERN.search(message))
        wants_download = bool(DOWNLOAD_INTENT_PATTERN.search(message))
        wants_live_quiz_link = bool(LIVE_QUIZ_LINK_INTENT_PATTERN.search(message))
        recipient_emails = self._email_addresses_from_message(message)
        requested_format = self._explicit_export_format_from_message(message)
        requested_duration = self.parse_live_quiz_duration(message)

        save_step = self._first_step_with_tool(completed_steps, "library_save_quiz")
        if wants_folder_add and save_step is None:
            save_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="library_save_quiz",
                arguments={
                    "title": f"$steps.{generate_step.step_id}.result.title",
                    "question_type": f"$steps.{generate_step.step_id}.result.question_type",
                    "questions": f"$steps.{generate_step.step_id}.result.questions",
                    "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
                },
                depends_on=[generate_step.step_id],
                reason="The user asked to add the generated quiz to a folder, so it must be saved first.",
            )
            completed_steps.append(save_step)

        folder_step = self._first_step_with_tool(completed_steps, "folder_get_by_name")
        if wants_folder_add and folder_step is None:
            folder_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="folder_get_by_name",
                arguments={"name": folder_name},
                depends_on=[save_step.step_id] if save_step else [generate_step.step_id],
                reason="Resolve the target folder named by the user.",
            )
            completed_steps.append(folder_step)

        if wants_folder_add and self._first_step_with_tool(completed_steps, "folder_add_saved_quiz") is None:
            if save_step is not None and folder_step is not None:
                completed_steps.append(
                    PlanStep(
                        step_id=self._next_step_id(completed_steps),
                        tool_name="folder_add_saved_quiz",
                        arguments={
                            "folder_id": f"$steps.{folder_step.step_id}.result.folder_id",
                            "saved_quiz_id": f"$steps.{save_step.step_id}.result.saved_quiz_id",
                        },
                        depends_on=[save_step.step_id, folder_step.step_id],
                        reason="Add the saved generated quiz to the requested folder.",
                )
            )

        live_link_step = next((step for step in completed_steps if step.tool_name in LIVE_QUIZ_TOOLS), None)
        if wants_live_quiz_link and live_link_step is None:
            live_arguments: dict[str, Any] = {
                "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
            }
            if requested_duration is not None:
                live_arguments["duration"] = requested_duration
            live_link_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="live_quiz_ensure_access_link",
                arguments=live_arguments,
                depends_on=[generate_step.step_id],
                reason="Ensure the generated quiz has an active live quiz link.",
            )
            completed_steps.append(live_link_step)

        if (
            wants_live_quiz_link
            and recipient_emails
            and self._first_step_with_tool(completed_steps, "live_quiz_send_invites") is None
            and live_link_step is not None
        ):
            completed_steps.append(
                PlanStep(
                    step_id=self._next_step_id(completed_steps),
                    tool_name="live_quiz_send_invites",
                    arguments={
                        "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
                        "recipient_emails": recipient_emails,
                        "live_quiz_link": f"$steps.{live_link_step.step_id}.result.live_quiz_link",
                    },
                    requires_confirmation=True,
                    depends_on=[generate_step.step_id, live_link_step.step_id],
                    reason="Send the generated quiz live link to the requested recipients.",
                )
            )

        if wants_download and self._first_step_with_tool(completed_steps, "quiz_export_link") is None:
            export_arguments = {
                "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
            }
            if requested_format:
                export_arguments["format"] = requested_format
            completed_steps.append(
                PlanStep(
                    step_id=self._next_step_id(completed_steps),
                    tool_name="quiz_export_link",
                    arguments=export_arguments,
                    depends_on=[generate_step.step_id],
                    reason="Prepare the requested download for the generated quiz.",
                )
            )

        return completed_steps

    def _first_step_with_tool(self, steps: list[PlanStep], tool_name: str) -> PlanStep | None:
        return next((step for step in steps if step.tool_name == tool_name), None)

    def _next_step_id(self, steps: list[PlanStep]) -> str:
        existing_ids = {step.step_id for step in steps}
        index = len(existing_ids) + 1
        while f"step_{index}" in existing_ids:
            index += 1
        return f"step_{index}"

    def _folder_name_from_message(self, message: str) -> str | None:
        match = FOLDER_NAME_PATTERN.search(message)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _explicit_export_format_from_message(self, message: str) -> str | None:
        for pattern, file_format in EXPORT_FORMAT_PATTERNS:
            if pattern.search(message):
                return file_format
        return None

    def _email_addresses_from_message(self, message: str) -> list[str]:
        seen: set[str] = set()
        emails: list[str] = []
        for match in EMAIL_ADDRESS_PATTERN.finditer(message):
            email = match.group(0).lower()
            if email not in seen:
                seen.add(email)
                emails.append(email)
        return emails

    def _normalize_live_quiz_duration(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        duration = self.parse_live_quiz_duration(message)
        for step in steps:
            if step.tool_name in {"live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
                if duration is not None:
                    step.arguments["duration"] = duration
                elif step.tool_name == "live_quiz_create_access_link":
                    step.arguments.pop("duration", None)
        return steps

    def _message_explicitly_supplies_live_quiz_duration(self, message: str) -> bool:
        return self.parse_live_quiz_duration(message) is not None

    def parse_live_quiz_duration(self, message: str) -> int | None:
        for pattern in LIVE_QUIZ_DURATION_VALUE_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue
            value = int(match.group(1))
            unit = (match.group(2) or "minutes").lower()
            if unit.startswith(("hour", "hr")):
                return value * 60
            return value
        return None

    def normalize_live_quiz_identity(
        self,
        steps: list[PlanStep],
        message: str,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> list[PlanStep]:
        live_steps = [step for step in steps if step.tool_name in LIVE_QUIZ_TOOLS]
        if not live_steps:
            return steps
        if any(
            step.tool_name == "live_quiz_create_access_link"
            and not self._has_generation_argument(step.arguments.get("duration"))
            for step in live_steps
        ):
            return steps
        if all(
            self._is_resolved_quiz_reference(
                step.arguments.get("quiz_id"),
                page_context=page_context,
                recent_artifacts=recent_artifacts,
            )
            for step in live_steps
        ):
            return steps

        existing_lookup = self._first_step_with_tool(steps, "library_find_saved_quiz_by_title")
        if existing_lookup is not None:
            lookup_step = existing_lookup
        else:
            title = self._live_quiz_title_from_steps_or_message(live_steps, message)
            if not title:
                return steps
            lookup_step = PlanStep(
                step_id=self._next_step_id(steps),
                tool_name="library_find_saved_quiz_by_title",
                arguments={"title": title},
                reason="Resolve the named quiz to its canonical quiz id before managing live quiz links.",
            )
            steps = self._insert_before_first_live_quiz_step(steps, lookup_step)

        for step in steps:
            if step.tool_name not in LIVE_QUIZ_TOOLS:
                continue
            quiz_id = step.arguments.get("quiz_id")
            if self._is_resolved_quiz_reference(
                quiz_id,
                page_context=page_context,
                recent_artifacts=recent_artifacts,
            ):
                continue
            step.arguments["quiz_id"] = f"$steps.{lookup_step.step_id}.result.quiz_id"
            if lookup_step.step_id not in step.depends_on:
                step.depends_on = [*step.depends_on, lookup_step.step_id]

        return steps

    def _insert_before_first_live_quiz_step(self, steps: list[PlanStep], lookup_step: PlanStep) -> list[PlanStep]:
        for index, step in enumerate(steps):
            if step.tool_name in LIVE_QUIZ_TOOLS:
                return [*steps[:index], lookup_step, *steps[index:]]
        return [*steps, lookup_step]

    def _live_quiz_title_from_steps_or_message(self, live_steps: list[PlanStep], message: str) -> str | None:
        for step in live_steps:
            quiz_id = step.arguments.get("quiz_id")
            if isinstance(quiz_id, str) and quiz_id.strip() and not self._is_resolved_quiz_reference(quiz_id):
                title = self._clean_quiz_title_candidate(quiz_id)
                if title:
                    return title
            for key in ("title", "quiz_title", "name"):
                value = step.arguments.get(key)
                if isinstance(value, str):
                    title = self._clean_quiz_title_candidate(value)
                    if title:
                        return title

        patterns = (
            r"\bquiz\s+(?:on|about|named|called|titled)\s+(.+?)(?:\s+(?:currently|already|have|has|with|for|to|and)\b|[?.!,]|$)",
            r"\b(?:live\s+quiz\s+link|live\s+link|access\s+link|attempt\s+link|participant\s+link)\s+(?:for|on)\s+(.+?)(?:[?.!,]|$)",
            r"\b(?:for|on)\s+(?:my\s+|the\s+)?(.+?)\s+quiz\b",
        )
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                title = self._clean_quiz_title_candidate(match.group(1))
                if title:
                    return title
        return None

    def _clean_quiz_title_candidate(self, value: str) -> str | None:
        candidate = re.sub(r"\s+", " ", value).strip(" .?!,;:'\"")
        if not candidate:
            return None
        generic_values = {
            "quiz",
            "the quiz",
            "this quiz",
            "that quiz",
            "it",
            "the one",
            "the above",
            "the quiz above",
        }
        if candidate.lower() in generic_values:
            return None
        return candidate

    def _is_resolved_quiz_reference(
        self,
        value: Any,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> bool:
        if not isinstance(value, str):
            return self._has_generation_argument(value)
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.startswith("$steps.") or stripped.startswith("$context."):
            return True
        if CANONICAL_ID_PATTERN.fullmatch(stripped):
            return True
        id_keys = ("quiz_id", "id", "canonical_quiz_id", "current_quiz_id")
        if page_context and find_title_for_id(page_context, stripped, id_keys=id_keys):
            return True
        for artifact in recent_artifacts or []:
            if find_title_for_id(artifact, stripped, id_keys=id_keys):
                return True
        return False

    def _canonical_question_type_from_text(self, text: str) -> str | None:
        for pattern, question_type in QUESTION_TYPE_PATTERNS:
            if pattern.search(text):
                return question_type
        return None

    def _message_explicitly_requests_generation(self, message: str) -> bool:
        if self._verb_before_quiz_content_request(message):
            return True
        if LIVE_QUIZ_LINK_ONLY_CREATION_PATTERN.search(message):
            return False
        return bool(GENERATION_INTENT_PATTERN.search(message) and not LIVE_QUIZ_LINK_INTENT_PATTERN.search(message))

    def _verb_before_quiz_content_request(self, message: str) -> bool:
        verb_pattern = re.compile(rf"\b{GENERATION_VERBS_PATTERN}\b", re.IGNORECASE)
        quiz_pattern = re.compile(rf"\b{QUIZ_NOUN_PATTERN}\b", re.IGNORECASE)
        link_terms = re.compile(r"\b(link|access|invite|attempt|participant|code)\b", re.IGNORECASE)
        content_cues = re.compile(r"^\s*(?:on|about|for|with|covering|regarding)\b|[,.;!?]", re.IGNORECASE)
        for verb_match in verb_pattern.finditer(message):
            suffix = message[verb_match.end() : verb_match.end() + 180]
            quiz_match = quiz_pattern.search(suffix)
            if quiz_match is None:
                continue
            between = suffix[: quiz_match.start()]
            after = suffix[quiz_match.end() : quiz_match.end() + 60]
            if link_terms.search(between) or link_terms.match(after.strip()):
                continue
            if content_cues.search(after):
                return True
        return False

    @staticmethod
    def _has_generation_argument(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return True



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
