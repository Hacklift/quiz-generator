from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from server.app.assistant.schemas import ToolResult
from server.app.assistant.tool_policy import ToolDefinition, get_tool_definition


class PreparationStatus(StrEnum):
    READY = "ready"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"


@dataclass(frozen=True)
class ArgumentProblem:
    field: str
    code: str
    message: str
    candidates: tuple[Any, ...] = ()


@dataclass(frozen=True)
class ArgumentPreparationResult:
    status: PreparationStatus
    arguments: dict[str, Any]
    problems: tuple[ArgumentProblem, ...] = ()
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def missing_fields(self) -> list[str]:
        return [problem.field for problem in self.problems if problem.code == "missing"]

    @property
    def needs_model_assistance(self) -> bool:
        return self.status is PreparationStatus.AMBIGUOUS


class StepPreparationPipeline:
    """Deterministically binds and validates one planned tool call.

    Model assistance is deliberately outside this class. The caller may request
    it only when this pipeline reports semantic ambiguity, then run preparation
    again on the model-proposed arguments.
    """

    def prepare(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        previous_results: list[ToolResult],
        user_id: str | None,
    ) -> ArgumentPreparationResult:
        tool = get_tool_definition(tool_name)
        provenance: dict[str, str] = {}
        unresolved: list[ArgumentProblem] = []
        resolved = self._bind_value(
            arguments,
            previous_results=previous_results,
            user_id=user_id,
            path="",
            provenance=provenance,
            unresolved=unresolved,
        )
        assert isinstance(resolved, dict)

        if unresolved:
            return ArgumentPreparationResult(
                status=PreparationStatus.AMBIGUOUS,
                arguments=resolved,
                problems=tuple(unresolved),
                provenance=provenance,
            )

        problems = self._validate(tool, resolved)
        if any(problem.code == "missing" for problem in problems):
            status = PreparationStatus.MISSING
        elif problems:
            status = PreparationStatus.INVALID
        else:
            status = PreparationStatus.READY
        return ArgumentPreparationResult(
            status=status,
            arguments=resolved,
            problems=tuple(problems),
            provenance=provenance,
        )

    def _bind_value(
        self,
        value: Any,
        *,
        previous_results: list[ToolResult],
        user_id: str | None,
        path: str,
        provenance: dict[str, str],
        unresolved: list[ArgumentProblem],
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: self._bind_value(
                    item,
                    previous_results=previous_results,
                    user_id=user_id,
                    path=f"{path}.{key}" if path else key,
                    provenance=provenance,
                    unresolved=unresolved,
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [
                self._bind_value(
                    item,
                    previous_results=previous_results,
                    user_id=user_id,
                    path=f"{path}[{index}]",
                    provenance=provenance,
                    unresolved=unresolved,
                )
                for index, item in enumerate(value)
            ]
        if not isinstance(value, str) or not value.startswith("$"):
            if path:
                provenance.setdefault(path, "planner")
            return value

        if value == "$context.user_id" and user_id:
            provenance[path] = "user_context"
            return user_id

        reference = _parse_step_reference(value)
        if reference is not None:
            step_id, field_name = reference
            matches = [result for result in previous_results if result.step_id == step_id and result.ok]
            if len(matches) == 1 and field_name in matches[0].data:
                provenance[path] = f"tool_result:{step_id}"
                return matches[0].data[field_name]

        unresolved.append(
            ArgumentProblem(
                field=path or "arguments",
                code="ambiguous_reference",
                message=f"Could not deterministically resolve {value}.",
                candidates=(value,),
            )
        )
        return value

    def _validate(self, tool: ToolDefinition, arguments: dict[str, Any]) -> list[ArgumentProblem]:
        problems: list[ArgumentProblem] = []
        required = list(tool.required_arguments)
        if tool.name == "library_save_quiz" and not _has_value(arguments.get("quiz_id")):
            required.extend(["title", "question_type", "questions"])

        for name in dict.fromkeys(required):
            if not _has_value(arguments.get(name)):
                problems.append(
                    ArgumentProblem(field=name, code="missing", message=f"{name} is required.")
                )

        for name, value in arguments.items():
            definition = tool.argument_definition(name)
            if definition is None or value is None or not _has_value(value):
                continue
            expected_type = definition.get("type")
            if expected_type and not _matches_type(value, expected_type):
                problems.append(
                    ArgumentProblem(
                        field=name,
                        code="invalid_type",
                        message=f"{name} must be {expected_type}.",
                    )
                )
                continue
            allowed = definition.get("allowed_values")
            if allowed and value not in allowed:
                problems.append(
                    ArgumentProblem(
                        field=name,
                        code="invalid_value",
                        message=f"{name} must be one of: {', '.join(map(str, allowed))}.",
                        candidates=tuple(allowed),
                    )
                )
        return problems


def _parse_step_reference(value: str) -> tuple[str, str] | None:
    prefix = "$steps."
    marker = ".result."
    if not value.startswith(prefix) or marker not in value:
        return None
    step_id, field_name = value[len(prefix) :].split(marker, 1)
    if not step_id or not field_name or "." in field_name:
        return None
    return step_id, field_name


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
