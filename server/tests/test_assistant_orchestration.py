import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")

import pytest
from fastapi import HTTPException

from server.app.assistant.artifacts import infer_artifacts_from_results
from server.app.assistant.error_mapper import tool_error_message
from server.app.assistant.model_router import AssistantModelRouter
from server.app.assistant.orchestrator import GENERATION_INTENT_PATTERN, QUESTION_TYPE_PATTERNS
from server.app.assistant.pending_runs import InMemoryAssistantRunStore
from server.app.assistant.providers import AssistantProviderError
from server.app.assistant.schemas import (
    AssistantFinalResponse,
    AssistantChatRequest,
    ExecutorDecision,
    PlanStep,
    PlannerDecision,
    ToolResult,
)
from server.app.assistant.service import AssistantService
from server.app.assistant.tool_policy import public_tool_catalog
from server.app.core.config import settings
from server.app.users.models import UserOut


def make_service(model_router, mcp_client):
    return AssistantService(
        model_router=model_router,
        mcp_client=mcp_client,
        pending_run_store=InMemoryAssistantRunStore(),
    )


class FakeProvider:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[str] = []

    async def generate(self, *, messages, model, temperature=0):
        self.calls.append(model)
        return self.responses.pop(0)


class ProviderErrorModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        raise AssistantProviderError("Gemini request failed: 429 RESOURCE_EXHAUSTED quota details")

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not run when planner provider fails.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response should not run when planner provider fails.")


class FakeModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_folder",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="folder_create",
                    arguments={"name": "Biology Practice"},
                    requires_confirmation=True,
                    reason="User asked to create a folder.",
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        return ExecutorDecision(step_id="step_1", tool_name="folder_create", arguments={"name": "Biology Practice"})

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        return AssistantFinalResponse(message="Done.", artifacts=[])


class FakeMcpClient:
    def __init__(self):
        self.called = False
        self.calls: list[dict] = []

    async def call_tool(self, **kwargs):
        self.called = True
        self.calls.append(kwargs)
        tool_name = kwargs["tool_name"]
        if tool_name == "quiz_generate":
            title = kwargs["arguments"].get("profession") or "Biology Quiz"
            return {
                "quiz_id": "quiz-1",
                "history_id": "history-1",
                "title": title,
                "question_type": kwargs["arguments"].get("question_type") or "multichoice",
                "question_count": 1,
                "questions": [
                    {
                        "question": "What is biology?",
                        "options": ["Life", "Math"],
                        "answer": "Life",
                        "question_type": "Multiple Choice",
                    }
                ],
            }
        if tool_name == "library_save_quiz":
            return {"saved_quiz_id": "saved-1", "quiz_id": kwargs["arguments"].get("quiz_id")}
        if tool_name == "library_find_saved_quiz_by_title":
            return {
                "query": kwargs["arguments"].get("title"),
                "found": True,
                "saved_quiz_id": "saved-1",
                "quiz_id": "quiz-1",
                "title": kwargs["arguments"].get("title"),
                "matches": [
                    {
                        "id": "saved-1",
                        "saved_quiz_id": "saved-1",
                        "quiz_id": "quiz-1",
                        "title": kwargs["arguments"].get("title"),
                    }
                ],
            }
        if tool_name == "folder_create":
            return {"id": "folder-1", "folder_id": "folder-1", "name": kwargs["arguments"].get("name")}
        if tool_name == "folder_get_by_name":
            return {
                "found": True,
                "id": "folder-1",
                "folder_id": "folder-1",
                "name": kwargs["arguments"].get("name"),
                "quizzes": [],
            }
        if tool_name == "folder_add_saved_quiz":
            return {
                "id": "folder-item-1",
                "folder_item_id": "folder-item-1",
                "folder_id": kwargs["arguments"].get("folder_id"),
                "saved_quiz_id": kwargs["arguments"].get("saved_quiz_id"),
                "quiz_id": "quiz-1",
                "title": "Nigerian Geopolitics",
            }
        if tool_name == "quiz_export_link":
            return {
                "quiz_id": kwargs["arguments"].get("quiz_id"),
                "format": kwargs["arguments"].get("format"),
                "href": "/download-quiz",
                "filename": f"quiz.{kwargs['arguments'].get('format')}",
            }
        if tool_name == "share_create_link":
            quiz_id = kwargs["arguments"].get("quiz_id")
            return {"link": f"http://localhost:3000/share/{quiz_id}", "quiz_id": quiz_id}
        if tool_name == "share_send_email":
            return {
                "message": "Email sent successfully.",
                "quiz_id": kwargs["arguments"].get("quiz_id"),
                "recipient_email": kwargs["arguments"].get("recipient_email"),
                "link": kwargs["arguments"].get("shareable_link"),
            }
        if tool_name == "live_quiz_get_access_link":
            quiz_id = kwargs["arguments"].get("quiz_id")
            return {
                "found": True,
                "quiz_id": quiz_id,
                "title": "Database Sharding",
                "live_quiz_link": "http://localhost:3000/quiz-access/ABC123",
                "access_code": "ABC123",
                "reused_existing": True,
            }
        if tool_name == "live_quiz_ensure_access_link":
            quiz_id = kwargs["arguments"].get("quiz_id")
            duration = kwargs["arguments"].get("duration")
            if duration is None:
                return {
                    "found": False,
                    "requires_duration": True,
                    "quiz_id": quiz_id,
                    "title": "Circuit Breaker in systems design",
                    "message": "Quiz duration is required to create a new live quiz link.",
                }
            return {
                "found": True,
                "requires_duration": False,
                "quiz_id": quiz_id,
                "title": "Circuit Breaker in systems design",
                "live_quiz_link": "http://localhost:3000/quiz-access/NEW123",
                "access_code": "NEW123",
                "duration": duration,
                "time_limit_minutes": duration,
                "reused_existing": False,
            }
        if tool_name == "live_quiz_send_invites":
            recipients = kwargs["arguments"].get("recipient_emails") or []
            return {
                "quiz_id": kwargs["arguments"].get("quiz_id"),
                "title": "Database Sharding",
                "sent_count": len(recipients),
                "failed_count": 0,
                "recipients": recipients,
            }
        return {"ok": True}


class ErrorMcpClient(FakeMcpClient):
    async def call_tool(self, **kwargs):
        self.called = True
        self.calls.append(kwargs)
        return {"isError": True, "error": "Generation provider failed."}


class LimitErrorMcpClient(FakeMcpClient):
    async def call_tool(self, **kwargs):
        self.called = True
        self.calls.append(kwargs)
        return {
            "isError": True,
            "error": "Error executing tool quiz_generate: 422: Quiz generation is limited to 10 questions.",
        }


class MissingFolderMcpClient(FakeMcpClient):
    async def call_tool(self, **kwargs):
        tool_name = kwargs["tool_name"]
        if tool_name == "folder_get_by_name":
            self.called = True
            self.calls.append(kwargs)
            return {
                "found": False,
                "folder_id": None,
                "id": None,
                "name": kwargs["arguments"].get("name"),
                "quizzes": [],
            }
        return await super().call_tool(**kwargs)


class MultiStepModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_and_save",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "Biology",
                        "num_questions": 1,
                        "question_type": "Multiple Choice",
                        "difficulty_level": "Beginner",
                        "audience_type": "Students",
                    },
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="library_save_quiz",
                    arguments={
                        "title": "Biology Quiz",
                        "question_type": "Multiple Choice",
                        "questions": "$steps.step_1.result.questions",
                        "quiz_id": "$steps.step_1.result.quiz_id",
                    },
                    depends_on=["step_1"],
                ),
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed when placeholders resolve.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        return AssistantFinalResponse(message="Generated and saved the quiz.", artifacts=[])


class CreateFolderAndAddSavedQuizModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_folder_and_add_saved_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="folder_create",
                    arguments={"name": "Geopolitics"},
                    requires_confirmation=True,
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="library_find_saved_quiz_by_title",
                    arguments={"title": "Nigerian Geopolitics"},
                    depends_on=["step_1"],
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="folder_add_saved_quiz",
                    arguments={
                        "folder_id": "$steps.step_1.result.folder_id",
                        "saved_quiz_id": "$steps.step_2.result.saved_quiz_id",
                    },
                    requires_confirmation=True,
                    depends_on=["step_1", "step_2"],
                ),
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed when placeholders resolve.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic folder add result.")


class FolderExistenceModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="check_folder",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="folder_get_by_name",
                    arguments={"name": "Thermodynamics"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for folder lookup.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic folder lookup.")


class SaveAndAddToMissingFolderModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="save_and_add_to_folder",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="library_save_quiz",
                    arguments={
                        "title": "Thermal conductivity measurement",
                        "question_type": "multichoice",
                        "questions": [
                            {
                                "question": "What is thermal conductivity?",
                                "options": ["A", "B"],
                                "answer": "A",
                            }
                        ],
                        "quiz_id": "quiz-thermal",
                    },
                    requires_confirmation=True,
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="folder_get_by_name",
                    arguments={"name": "Thermodynamics"},
                    depends_on=["step_1"],
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="folder_add_saved_quiz",
                    arguments={
                        "folder_id": "$steps.step_2.result.folder_id",
                        "saved_quiz_id": "$steps.step_1.result.saved_quiz_id",
                    },
                    requires_confirmation=True,
                    depends_on=["step_1", "step_2"],
                ),
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed when placeholders resolve.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic recovery result.")


class GenerationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "JavaScript",
                        "num_questions": 1,
                        "question_type": "multichoice",
                        "difficulty_level": "Beginner",
                        "audience_type": "Students",
                    },
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be used for deterministic generation requests.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic generation result.")


class SaveHistoryArtifactModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="save_history_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="library_save_quiz",
                    arguments={"title": "Nigerian Insecurity"},
                    requires_confirmation=True,
                    reason="Save the selected history quiz.",
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for artifact-backed save.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        return AssistantFinalResponse(message="Saved and prepared the download.", artifacts=[])


class MissingArgumentLoopModelRouter:
    def __init__(self):
        self.plan_calls = 0

    async def plan(self, prompt: str) -> PlannerDecision:
        self.plan_calls += 1
        if self.plan_calls == 1:
            return PlannerDecision(
                intent="save_quiz",
                needs_tools=True,
                steps=[
                    PlanStep(
                        step_id="step_1",
                        tool_name="library_save_quiz",
                        arguments={"title": "Nigerian Insecurity"},
                        requires_confirmation=True,
                    )
                ],
            )
        return PlannerDecision(intent="general_chat", needs_tools=False, steps=[])

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        return AssistantFinalResponse(
            message="I can use quiz history items when they include a quiz reference.",
            artifacts=[],
        )


class IncompleteCompoundGenerationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "Database Sharding",
                        "num_questions": 3,
                        "question_type": "true-false",
                        "difficulty_level": "medium",
                    },
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for completed compound workflow.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic compound result.")


class AccidentalGenerateModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="add_existing_quiz_to_folder",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "Specific Heat",
                        "num_questions": 5,
                        "question_type": "Multiple Choice",
                        "difficulty_level": "Beginner",
                        "audience_type": "Students",
                    },
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not run for blocked accidental generation.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for blocked accidental generation.")


class MissingGenerationFieldsModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "Physics",
                        "question_type": "Multiple Choice",
                    },
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not fabricate missing generation fields.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for blocked generation.")


class MinimalGenerationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments={
                        "profession": "British Empire",
                        "num_questions": 3,
                        "question_type": "multichoice",
                    },
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for minimal valid generation arguments.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic generation result.")


class LiveQuizLinkMissingDurationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_create_access_link",
                    arguments={"quiz_id": "quiz-1"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not fabricate missing live quiz duration.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for missing live quiz duration.")


class LiveQuizLinkNamedQuizMissingDurationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_create_access_link",
                    arguments={"quiz_id": "Circuit Breaker in systems design"},
                    requires_confirmation=True,
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for live quiz slot filling.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run before confirmation.")


class LiveQuizConditionalLinkModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="ensure_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_get_access_link",
                    arguments={"quiz_id": "Circuit Breaker in systems design"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for live quiz ensure workflow.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic live quiz ensure result.")


class LiveQuizGetLinkWithTitleAsQuizIdModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="get_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_get_access_link",
                    arguments={"quiz_id": "Database Sharding"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed after title lookup insertion.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic live quiz link result.")


class LiveQuizLinkInventedDurationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_create_access_link",
                    arguments={"quiz_id": "quiz-1", "duration": 30},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not run when live quiz duration was not supplied by the user.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for missing live quiz duration.")


class LiveQuizLinkWithDurationModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="create_live_quiz_link",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="live_quiz_create_access_link",
                    arguments={"quiz_id": "quiz-1", "duration": 20},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for valid live quiz link arguments.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run before confirmation.")


class ExportQuizWithoutFormatModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="export_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_export_link",
                    arguments={"quiz_id": "quiz-1"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for export choice.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic export result.")


class ExportQuizWithLeakedFormatModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="export_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_export_link",
                    arguments={"quiz_id": "quiz-1", "format": "pdf"},
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for export choice.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic export result.")


class ExportAndShareQuizModelRouter:
    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="export_and_share_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_export_link",
                    arguments={"quiz_id": "quiz-1", "format": "pdf"},
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="share_create_link",
                    arguments={"quiz_id": "quiz-1"},
                    depends_on=["step_1"],
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="share_send_email",
                    arguments={
                        "quiz_id": "quiz-1",
                        "recipient_email": "chidiebereenwelunta@gmail.com",
                        "shareable_link": "$steps.step_2.result.link",
                    },
                    depends_on=["step_1", "step_2"],
                ),
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for export and share.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic export and share result.")


class ParameterizedGenerationModelRouter:
    def __init__(self, arguments: dict):
        self.arguments = arguments

    async def plan(self, prompt: str) -> PlannerDecision:
        return PlannerDecision(
            intent="generate_quiz",
            needs_tools=True,
            steps=[
                PlanStep(
                    step_id="step_1",
                    tool_name="quiz_generate",
                    arguments=self.arguments,
                )
            ],
        )

    async def execute(self, prompt: str) -> ExecutorDecision:
        raise AssertionError("Executor should not be needed for valid planner arguments.")

    async def final_response(self, prompt: str) -> AssistantFinalResponse:
        raise AssertionError("Final response model should not run for deterministic generation result.")


@pytest.mark.parametrize(
    "message",
    [
        "Generate 4 multiple-choice quizzes on the history of Nigerian geopolitics.",
        "Generate a multiple-choice quizze on the history of Nigerian geopolitics with 4 questions.",
        "Create 3 MCQ questions on JavaScript DSA.",
        "Build one true/false assessment about the British Empire.",
    ],
)
def test_generation_intent_detector_accepts_quiz_variants(message):
    assert GENERATION_INTENT_PATTERN.search(message)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Generate 4 multiple-choice quizzes on history.", "multichoice"),
        ("Generate 4 multi-choice questions on history.", "multichoice"),
        ("Generate 4 MCQ questions on history.", "multichoice"),
        ("Generate one true/false assessment on history.", "true-false"),
        ("Generate one true or false assessment on history.", "true-false"),
        ("Generate three short answer questions on history.", "short-answer"),
        ("Generate three open-ended questions on history.", "open-ended"),
    ],
)
def test_question_type_detector_accepts_common_aliases(message, expected):
    detected = [
        question_type
        for pattern, question_type in QUESTION_TYPE_PATTERNS
        if pattern.search(message)
    ]

    assert expected in detected


@pytest.mark.asyncio
async def test_model_router_retries_primary_then_uses_valid_response():
    provider = FakeProvider(
        [
            "not-json",
            '{"intent":"generate_quiz","needs_tools":true,"summary":null,'
            '"steps":[{"step_id":"step_1","tool_name":"quiz_generate","arguments":{},'
            '"requires_confirmation":false,"depends_on":[],"reason":null}],'
            '"final_response_style":"concise"}',
        ]
    )
    router = AssistantModelRouter.__new__(AssistantModelRouter)

    decision = await router._generate_validated(
        provider=provider,
        primary_model="primary-model",
        fallback_model="fallback-model",
        prompt="plan",
        response_model=PlannerDecision,
        role_name="planner",
    )

    assert decision.tool_name == "quiz_generate"
    assert decision.steps[0].tool_name == "quiz_generate"
    assert provider.calls == ["primary-model", "primary-model"]


def test_model_router_accepts_single_item_array_for_object_response():
    router = AssistantModelRouter.__new__(AssistantModelRouter)

    decision = router._parse_json_model(
        '[{"step_id":"step_2","tool_name":"quiz_export_link","arguments":{"quiz_id":"quiz-1","format":"pdf"}}]',
        ExecutorDecision,
    )

    assert decision.step_id == "step_2"
    assert decision.tool_name == "quiz_export_link"
    assert decision.arguments == {"quiz_id": "quiz-1", "format": "pdf"}


def test_model_router_repairs_trailing_commas_in_json_response():
    router = AssistantModelRouter.__new__(AssistantModelRouter)

    decision = router._parse_json_model(
        '{"intent":"answer","needs_tools":true,"summary":null,'
        '"steps":[{"step_id":"step_1","tool_name":"quiz_get_answers","arguments":{"quiz_id":"quiz-1",},'
        '"requires_confirmation":false,"depends_on":[],"reason":null,},],'
        '"final_response_style":"concise",}',
        PlannerDecision,
    )

    assert decision.tool_name == "quiz_get_answers"


def test_expired_token_tool_error_is_polished():
    message = tool_error_message("quiz_get_answers", {"error": "Token has expired"})

    assert message == "Your session expired. Please log in again, then retry this request."


@pytest.mark.asyncio
async def test_assistant_requests_confirmation_before_write_tool(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", True)
    mcp_client = FakeMcpClient()
    service = make_service(FakeModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Create a folder called Biology Practice"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.actions
    assert response.actions[0].tool_name == "folder_create"
    assert response.actions[0].arguments == {"name": "Biology Practice"}
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_returns_polished_login_prompt_for_authenticated_tools(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(FakeModelRouter(), mcp_client)

    response = await service.chat(
        request=AssistantChatRequest(message="Create a folder called Biology Practice"),
        user=None,
        authorization_header=None,
    )

    assert response.message == (
        "Please log in to access your folders, saved quizzes, history, downloads, sharing, "
        "and other personal assistant features."
    )
    assert response.actions == []
    assert response.artifacts == []
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_returns_generation_specific_login_prompt(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(GenerationModelRouter(), mcp_client)

    response = await service.chat(
        request=AssistantChatRequest(message="Generate a multichoice quiz on Biology with 3 questions."),
        user=None,
        authorization_header=None,
    )

    assert response.message == "Please log in to generate quizzes."
    assert response.actions == []
    assert response.artifacts == []
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_reuses_history_artifact_for_save_and_download(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(SaveHistoryArtifactModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(
            message="Go ahead and save the Nigerian Insecurity quiz from history and also download it for me.",
            recent_artifacts=[
                {
                    "type": "resource_list",
                    "data": {
                        "resource": "quiz_history",
                        "title": "Quiz History",
                        "items": [
                            {
                                "id": "history-1",
                                "label": "Nigerian Insecurity",
                                "href": "/quiz_history/history-1",
                                "metadata": {
                                    "id": "history-1",
                                    "quiz_id": "quiz-history-1",
                                    "title": "Nigerian Insecurity",
                                    "question_type": "multichoice",
                                },
                            }
                        ],
                    },
                }
            ],
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "Please confirm: save Nigerian Insecurity to your library."
    assert response.actions[0].tool_name == "library_save_quiz"
    assert response.actions[0].arguments["quiz_id"] == "quiz-history-1"
    assert response.actions[0].arguments["title"] == "Nigerian Insecurity"
    assert "questions" not in response.actions[0].arguments
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_replans_missing_argument_follow_up_instead_of_looping(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    router = MissingArgumentLoopModelRouter()
    service = make_service(router, mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(message="Save the Nigerian Insecurity quiz."),
        user=user,
        authorization_header="Bearer token",
    )

    assert "questions before I can save the quiz" in first_response.message

    second_response = await service.chat(
        request=AssistantChatRequest(
            message="Are you saying you cannot pull the quiz from my history?",
            conversation_id=first_response.conversation_id,
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert second_response.message == "I can use quiz history items when they include a quiz reference."
    assert router.plan_calls == 2
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_sanitizes_provider_errors(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    service = make_service(ProviderErrorModelRouter(), FakeMcpClient())

    with pytest.raises(HTTPException) as exc_info:
        await service.chat(
            request=AssistantChatRequest(message="Generate a quiz on JavaScript."),
            user=None,
            authorization_header=None,
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "The assistant model is temporarily unavailable. Please retry shortly."
    assert "RESOURCE_EXHAUSTED" not in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_assistant_executes_multi_step_plan_with_resolved_placeholders(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", False)
    mcp_client = FakeMcpClient()
    service = make_service(MultiStepModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate one multichoice Biology quiz and save it"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I generated Biology and saved it."
    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_generate", "library_save_quiz"]
    assert mcp_client.calls[1]["arguments"]["quiz_id"] == "quiz-1"
    assert mcp_client.calls[1]["arguments"]["questions"][0]["question"] == "What is biology?"


@pytest.mark.asyncio
async def test_assistant_resumes_pending_plan_after_write_confirmation(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", True)
    mcp_client = FakeMcpClient()
    service = make_service(CreateFolderAndAddSavedQuizModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(
            message="Create a new folder called Geopolitics and add Nigerian Geopolitics to it",
            conversation_id="conversation-1",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert first_response.actions
    assert first_response.actions[0].tool_name == "folder_create"
    assert mcp_client.calls == []

    second_response = await service.chat(
        request=AssistantChatRequest(
            message="Create folder",
            conversation_id="conversation-1",
            confirmed_action={
                "run_id": first_response.actions[0].run_id,
                "step_id": first_response.actions[0].step_id,
                "tool_name": first_response.actions[0].tool_name,
                "arguments": first_response.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "folder_create",
        "library_find_saved_quiz_by_title",
    ]
    assert second_response.actions
    assert second_response.actions[0].tool_name == "folder_add_saved_quiz"
    assert second_response.actions[0].arguments == {
        "folder_id": "folder-1",
        "saved_quiz_id": "saved-1",
    }
    assert second_response.artifacts == []

    final_response = await service.chat(
        request=AssistantChatRequest(
            message="Add quiz to folder",
            conversation_id="conversation-1",
            confirmed_action={
                "run_id": second_response.actions[0].run_id,
                "step_id": second_response.actions[0].step_id,
                "tool_name": second_response.actions[0].tool_name,
                "arguments": second_response.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "folder_create",
        "library_find_saved_quiz_by_title",
        "folder_add_saved_quiz",
    ]
    assert final_response.message == (
        "I created Geopolitics and added Nigerian Geopolitics to Geopolitics."
    )
    assert len(final_response.artifacts) == 1
    assert final_response.artifacts[0].type == "status"
    assert final_response.artifacts[0].data["resource"] == "folder_item"
    assert final_response.artifacts[0].data["label"] == "Added Nigerian Geopolitics to Geopolitics."


@pytest.mark.asyncio
async def test_assistant_reports_named_folder_not_found(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = MissingFolderMcpClient()
    service = make_service(FolderExistenceModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Do I have a folder named Thermodynamics?"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "You do not have a folder named Thermodynamics."
    assert [call["tool_name"] for call in mcp_client.calls] == ["folder_get_by_name"]


@pytest.mark.asyncio
async def test_assistant_recovers_missing_folder_before_add_saved_quiz(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", True)
    mcp_client = MissingFolderMcpClient()
    service = make_service(SaveAndAddToMissingFolderModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    save_confirmation = await service.chat(
        request=AssistantChatRequest(
            message="Add the new Thermal conductivity measurement quiz above to the Thermodynamics folder",
            conversation_id="conversation-2",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert save_confirmation.actions
    assert save_confirmation.actions[0].tool_name == "library_save_quiz"
    assert mcp_client.calls == []

    create_folder_confirmation = await service.chat(
        request=AssistantChatRequest(
            message="Save quiz",
            conversation_id="conversation-2",
            confirmed_action={
                "run_id": save_confirmation.actions[0].run_id,
                "step_id": save_confirmation.actions[0].step_id,
                "tool_name": save_confirmation.actions[0].tool_name,
                "arguments": save_confirmation.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_save_quiz",
        "folder_get_by_name",
    ]
    assert create_folder_confirmation.message == (
        "You do not have a folder named Thermodynamics. "
        "Confirm if you want me to create it and continue adding the quiz."
    )
    assert create_folder_confirmation.actions
    assert create_folder_confirmation.actions[0].tool_name == "folder_create"
    assert create_folder_confirmation.actions[0].arguments == {"name": "Thermodynamics"}

    add_quiz_confirmation = await service.chat(
        request=AssistantChatRequest(
            message="Create Thermodynamics folder",
            conversation_id="conversation-2",
            confirmed_action={
                "run_id": create_folder_confirmation.actions[0].run_id,
                "step_id": create_folder_confirmation.actions[0].step_id,
                "tool_name": create_folder_confirmation.actions[0].tool_name,
                "arguments": create_folder_confirmation.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_save_quiz",
        "folder_get_by_name",
        "folder_create",
    ]
    assert add_quiz_confirmation.actions
    assert add_quiz_confirmation.actions[0].tool_name == "folder_add_saved_quiz"
    assert add_quiz_confirmation.actions[0].arguments == {
        "folder_id": "folder-1",
        "saved_quiz_id": "saved-1",
    }

    final_response = await service.chat(
        request=AssistantChatRequest(
            message="Add quiz to folder",
            conversation_id="conversation-2",
            confirmed_action={
                "run_id": add_quiz_confirmation.actions[0].run_id,
                "step_id": add_quiz_confirmation.actions[0].step_id,
                "tool_name": add_quiz_confirmation.actions[0].tool_name,
                "arguments": add_quiz_confirmation.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_save_quiz",
        "folder_get_by_name",
        "folder_create",
        "folder_add_saved_quiz",
    ]
    assert final_response.message == (
        "I saved the quiz, created Thermodynamics, and added Nigerian Geopolitics to Thermodynamics."
    )


@pytest.mark.asyncio
async def test_assistant_generates_quiz_from_planner_arguments(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(GenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate one multichoice quiz on JavaScript."),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I generated JavaScript."
    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_generate"]
    assert mcp_client.calls[0]["arguments"]["profession"] == "JavaScript"
    assert mcp_client.calls[0]["arguments"]["num_questions"] == 1
    assert mcp_client.calls[0]["arguments"]["question_type"] == "multichoice"


@pytest.mark.asyncio
async def test_assistant_completes_incomplete_compound_generate_folder_download_plan(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", False)
    mcp_client = FakeMcpClient()
    service = make_service(IncompleteCompoundGenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(
            message=(
                "Generate a true or false quiz on Database Sharding with 3 questions of medium "
                "difficulty, then add it to my Software Engineering folder and download it for me too"
            ),
            conversation_id="conversation-compound",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "quiz_generate",
        "library_save_quiz",
        "folder_get_by_name",
        "folder_add_saved_quiz",
    ]
    assert mcp_client.calls[2]["arguments"] == {"name": "Software Engineering"}
    assert response.message == "Choose a file format for the quiz download."
    assert [action.label for action in response.actions] == ["PDF", "DOCX", "TXT", "JSON"]


@pytest.mark.asyncio
async def test_assistant_completes_generated_quiz_folder_live_invite_plan(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", False)
    mcp_client = FakeMcpClient()
    service = make_service(IncompleteCompoundGenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(
            message=(
                "Generate a multichoice quiz on API designs, with medium difficulty and 5 questions, "
                "save it in the Software Engineering folder and send a live quiz link for it to "
                "emmanuelenwelunta@gmail.com, chidiebereenwelunta@gmail.com with 3 minutes duration"
            ),
            conversation_id="conversation-live-invite-compound",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "quiz_generate",
        "library_save_quiz",
        "folder_get_by_name",
        "folder_add_saved_quiz",
        "live_quiz_ensure_access_link",
    ]
    assert mcp_client.calls[4]["arguments"]["duration"] == 3
    assert first_response.actions
    assert first_response.actions[0].tool_name == "live_quiz_send_invites"
    assert first_response.actions[0].arguments["recipient_emails"] == [
        "emmanuelenwelunta@gmail.com",
        "chidiebereenwelunta@gmail.com",
    ]

    response = await service.chat(
        request=AssistantChatRequest(
            message=first_response.actions[0].label,
            conversation_id=first_response.conversation_id,
            confirmed_action={
                "type": first_response.actions[0].type,
                "run_id": first_response.actions[0].run_id,
                "step_id": first_response.actions[0].step_id,
                "tool_name": first_response.actions[0].tool_name,
                "arguments": first_response.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "quiz_generate",
        "library_save_quiz",
        "folder_get_by_name",
        "folder_add_saved_quiz",
        "live_quiz_ensure_access_link",
        "live_quiz_send_invites",
    ]
    assert mcp_client.calls[5]["arguments"]["recipient_emails"] == [
        "emmanuelenwelunta@gmail.com",
        "chidiebereenwelunta@gmail.com",
    ]
    assert "sent live quiz invites to 2 recipients" in response.message


@pytest.mark.asyncio
async def test_assistant_allows_generation_without_optional_difficulty_or_audience(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(MinimalGenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate 3 quiz, multichoice on British Empire"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I generated British Empire."
    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_generate"]
    assert mcp_client.calls[0]["arguments"] == {
        "profession": "British Empire",
        "num_questions": 3,
        "question_type": "multichoice",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "arguments"),
    [
        (
            "Generate 4 multiple-choice quizzes on the history of Nigerian geopolitics.",
            {
                "profession": "history of Nigerian geopolitics",
                "num_questions": 4,
                "question_type": "multichoice",
            },
        ),
        (
            "Generate a multiple-choice quizze on the history of Nigerian geopolitics with 4 questions.",
            {
                "profession": "history of Nigerian geopolitics",
                "num_questions": 4,
                "question_type": "multichoice",
            },
        ),
    ],
)
async def test_assistant_allows_generation_with_plural_and_typo_quiz_wording(
    monkeypatch,
    message,
    arguments,
):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(ParameterizedGenerationModelRouter(arguments), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message=message),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I generated history of Nigerian geopolitics."
    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_generate"]
    assert mcp_client.calls[0]["arguments"] == arguments


@pytest.mark.asyncio
async def test_assistant_asks_for_missing_generation_details_without_mcp(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(MissingGenerationFieldsModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate a quiz on JavaScript DSA."),
        user=user,
        authorization_header="Bearer token",
    )

    assert "question type" in response.message
    assert "number of questions" in response.message
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_resumes_quiz_generation_after_question_type_follow_up(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(
        ParameterizedGenerationModelRouter(
            {
                "profession": "API designs",
                "num_questions": 5,
                "question_type": "mutichoice",
            }
        ),
        mcp_client,
    )
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(
            message="Generate a mutichoice quiz on API designs, with 5 questions and medium difficulty.",
            conversation_id="conversation-generation-slot-fill",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert first_response.message == "I need the question type before generating a quiz."
    assert mcp_client.called is False

    second_response = await service.chat(
        request=AssistantChatRequest(
            message="question type is multichoice",
            conversation_id="conversation-generation-slot-fill",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert second_response.message == "I generated API designs."
    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_generate"]
    assert mcp_client.calls[0]["arguments"]["question_type"] == "multichoice"


@pytest.mark.asyncio
async def test_assistant_asks_for_live_quiz_duration_without_mcp(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizLinkMissingDurationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Create a live quiz link for this quiz."),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I need the live quiz duration before I can create the link."
    assert mcp_client.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize("duration_reply", ["use 3 minutes", "3 minutes."])
async def test_assistant_resumes_live_quiz_link_after_duration_follow_up(monkeypatch, duration_reply):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizLinkNamedQuizMissingDurationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(
            message="Create a live link for my quiz on Circuit Breaker in systems design."
        ),
        user=user,
        authorization_header="Bearer token",
    )
    assert first_response.message == "I need the live quiz duration before I can create the link."
    assert mcp_client.called is False

    second_response = await service.chat(
        request=AssistantChatRequest(
            message=duration_reply,
            conversation_id=first_response.conversation_id,
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == ["library_find_saved_quiz_by_title"]
    assert mcp_client.calls[0]["arguments"] == {"title": "Circuit Breaker in systems design"}
    assert second_response.message == "Please confirm: create a live quiz link for Circuit Breaker in systems design."
    assert second_response.actions[0].tool_name == "live_quiz_create_access_link"
    assert second_response.actions[0].arguments["quiz_id"] == "quiz-1"
    assert second_response.actions[0].arguments["duration"] == 3


@pytest.mark.asyncio
async def test_assistant_ensures_live_quiz_link_with_duration_follow_up(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizConditionalLinkModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    first_response = await service.chat(
        request=AssistantChatRequest(
            message="Check if my saved quiz on Circuit Breaker in systems design has a live quiz link; if not create one."
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert first_response.message == "I need the live quiz duration before I can create the link."
    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_find_saved_quiz_by_title",
        "live_quiz_ensure_access_link",
    ]
    assert mcp_client.calls[1]["arguments"]["quiz_id"] == "quiz-1"

    second_response = await service.chat(
        request=AssistantChatRequest(
            message="use 3 minutes",
            conversation_id=first_response.conversation_id,
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_find_saved_quiz_by_title",
        "live_quiz_ensure_access_link",
        "live_quiz_ensure_access_link",
    ]
    assert mcp_client.calls[2]["arguments"] == {"quiz_id": "quiz-1", "duration": 3}
    assert second_response.message == "I created a live quiz link for Circuit Breaker in systems design."
    assert second_response.artifacts[0].data["href"] == "http://localhost:3000/quiz-access/NEW123"


@pytest.mark.asyncio
async def test_assistant_resolves_named_quiz_before_live_link_lookup(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizGetLinkWithTitleAsQuizIdModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(
            message="Does the quiz on Database Sharding currently have a valid live link?"
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I found an active live quiz link for Database Sharding."
    assert [call["tool_name"] for call in mcp_client.calls] == [
        "library_find_saved_quiz_by_title",
        "live_quiz_get_access_link",
    ]
    assert mcp_client.calls[0]["arguments"] == {"title": "Database Sharding"}
    assert mcp_client.calls[1]["arguments"]["quiz_id"] == "quiz-1"
    assert len(response.artifacts) == 1
    assert response.artifacts[0].data["href"] == "http://localhost:3000/quiz-access/ABC123"


@pytest.mark.asyncio
async def test_assistant_rejects_model_invented_live_quiz_duration(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizLinkInventedDurationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Create a live quiz link for Database Sharding."),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I need the live quiz duration before I can create the link."
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_live_quiz_confirmation_uses_known_quiz_title(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(LiveQuizLinkWithDurationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(
            message="Create a live quiz link for 20 minutes.",
            recent_artifacts=[
                {
                    "type": "resource",
                    "data": {
                        "resource": "quiz",
                        "label": "Database Sharding",
                        "metadata": {"quiz_id": "quiz-1", "title": "Database Sharding"},
                    },
                }
            ],
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "Please confirm: create a live quiz link for Database Sharding."
    assert response.actions[0].tool_name == "live_quiz_create_access_link"
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_does_not_report_generation_success_for_mcp_error(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = ErrorMcpClient()
    service = make_service(GenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate one multichoice quiz on JavaScript."),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "I could not generate the quiz: Generation provider failed."
    assert mcp_client.called is True


@pytest.mark.asyncio
async def test_assistant_sanitizes_generation_limit_errors(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = LimitErrorMcpClient()
    service = make_service(GenerationModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate an open ended quiz on Electricity with 15 questions."),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "This quiz can have up to 10 questions. Try again with 10 or fewer."
    assert "quiz_generate" not in response.message
    assert "Error executing tool" not in response.message


@pytest.mark.asyncio
async def test_assistant_blocks_accidental_quiz_generation_for_follow_up_action(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(AccidentalGenerateModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Add Specific Heat to my Physics folder"),
        user=user,
        authorization_header="Bearer token",
    )

    assert "will not generate a new quiz" in response.message
    assert "list above" not in response.message
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_blocks_quiz_generation_when_required_fields_are_missing(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(MissingGenerationFieldsModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Generate a Physics quiz"),
        user=user,
        authorization_header="Bearer token",
    )

    assert "number of questions" in response.message
    assert mcp_client.called is False


@pytest.mark.asyncio
async def test_assistant_prompts_for_export_format_choice(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(ExportQuizWithoutFormatModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Export this quiz"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "Choose a file format for the quiz download."
    assert [action.type for action in response.actions] == ["choice", "choice", "choice", "choice"]
    assert [action.label for action in response.actions] == ["PDF", "DOCX", "TXT", "JSON"]
    assert mcp_client.calls == []

    final_response = await service.chat(
        request=AssistantChatRequest(
            message="PDF",
            conversation_id=response.conversation_id,
            confirmed_action={
                "type": response.actions[0].type,
                "run_id": response.actions[0].run_id,
                "step_id": response.actions[0].step_id,
                "tool_name": response.actions[0].tool_name,
                "arguments": response.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert mcp_client.calls[0]["tool_name"] == "quiz_export_link"
    assert mcp_client.calls[0]["arguments"] == {"quiz_id": "quiz-1", "format": "pdf"}
    assert "The download should start now" in final_response.message
    assert final_response.artifacts[0].type == "file_action"
    assert final_response.artifacts[0].data["auto_execute"] is True


@pytest.mark.asyncio
async def test_assistant_strips_unrequested_export_format_from_planner(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    mcp_client = FakeMcpClient()
    service = make_service(ExportQuizWithLeakedFormatModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(message="Download this quiz for me"),
        user=user,
        authorization_header="Bearer token",
    )

    assert response.message == "Choose a file format for the quiz download."
    assert [action.label for action in response.actions] == ["PDF", "DOCX", "TXT", "JSON"]
    assert mcp_client.calls == []


@pytest.mark.asyncio
async def test_assistant_holds_download_artifact_until_email_confirmation_completes(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_ENABLED", True)
    monkeypatch.setattr(settings, "ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES", True)
    mcp_client = FakeMcpClient()
    service = make_service(ExportAndShareQuizModelRouter(), mcp_client)
    user = UserOut(
        id="user-1",
        username="tester",
        email="tester@example.com",
        is_verified=True,
    )

    response = await service.chat(
        request=AssistantChatRequest(
            message="Export the quiz as PDF locally and share it with chidiebereenwelunta@gmail.com",
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == ["quiz_export_link", "share_create_link"]
    assert response.actions
    assert response.actions[0].tool_name == "share_send_email"
    assert response.artifacts == []
    assert response.message == "Please confirm: send this quiz link to chidiebereenwelunta@gmail.com."

    final_response = await service.chat(
        request=AssistantChatRequest(
            message="Send quiz email",
            conversation_id=response.conversation_id,
            confirmed_action={
                "run_id": response.actions[0].run_id,
                "step_id": response.actions[0].step_id,
                "tool_name": response.actions[0].tool_name,
                "arguments": response.actions[0].arguments,
            },
        ),
        user=user,
        authorization_header="Bearer token",
    )

    assert [call["tool_name"] for call in mcp_client.calls] == [
        "quiz_export_link",
        "share_create_link",
        "share_send_email",
    ]
    assert "Click the Download quiz button below" in final_response.message
    assert [artifact.type for artifact in final_response.artifacts] == [
        "file_action",
        "resource",
        "status",
    ]


def test_assistant_tool_catalog_excludes_quiz_grading():
    tool_names = {tool["name"] for tool in public_tool_catalog()}

    assert "quiz_grade_answers" not in tool_names
    assert "live_quiz_get_access_link" in tool_names
    assert "live_quiz_create_access_link" in tool_names
    assert "live_quiz_send_invites" in tool_names


def test_live_quiz_link_artifact_includes_copy_action():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="live_quiz_create_access_link",
                data={
                    "found": True,
                    "quiz_id": "quiz-1",
                    "title": "Systems Design",
                    "live_quiz_link": "http://localhost:3000/quiz-access/ABC123",
                    "access_code": "ABC123",
                    "reused_existing": False,
                },
            )
        ]
    )

    assert len(artifacts) == 1
    assert artifacts[0].type == "resource"
    assert artifacts[0].data["resource"] == "live_quiz_link"
    assert artifacts[0].data["href"] == "http://localhost:3000/quiz-access/ABC123"
    assert artifacts[0].data["actions"] == [
        {
            "type": "copy_to_clipboard",
            "label": "Copy link",
            "value": "http://localhost:3000/quiz-access/ABC123",
        }
    ]


def test_failed_live_quiz_link_result_does_not_create_artifact():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                ok=False,
                step_id="step_1",
                tool_name="live_quiz_get_access_link",
                data={"error": "Quiz not found"},
            )
        ]
    )

    assert artifacts == []


def test_live_quiz_invite_artifact_summarizes_batch_result():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="live_quiz_send_invites",
                data={
                    "sent_count": 2,
                    "failed_count": 1,
                    "sent": ["one@example.com", "two@example.com"],
                    "failed": [{"email": "bad@example.com", "error": "failed"}],
                },
            )
        ]
    )

    assert len(artifacts) == 1
    assert artifacts[0].type == "status"
    assert artifacts[0].data["resource"] == "live_quiz_invite"
    assert artifacts[0].data["label"] == "Sent quiz invites to 2 recipients; 1 failed."


def test_live_quiz_invite_status_artifact_can_be_suppressed_for_final_summary():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="live_quiz_send_invites",
                data={
                    "sent_count": 2,
                    "failed_count": 0,
                    "sent": ["one@example.com", "two@example.com"],
                    "failed": [],
                },
            )
        ],
        suppress_final_status_tools={"live_quiz_send_invites"},
    )

    assert artifacts == []


def test_answer_key_artifact_uses_recent_display_title_over_canonical_title():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="quiz_get_answers",
                data={
                    "quiz_id": "quiz-1",
                    "title": "Physics",
                    "question_type": "multichoice",
                    "answer_count": 1,
                    "answers": [
                        {
                            "question_number": 1,
                            "question": "What is specific heat?",
                            "answer": "Stored answer",
                        }
                    ],
                },
            )
        ],
        recent_artifacts=[
            {
                "type": "resource_list",
                "data": {
                    "resource": "folder_quiz",
                    "title": "Thermodynamics Folder",
                    "metadata": {
                        "folder_name": "Thermodynamics",
                        "display_title": "Thermodynamics Folder",
                    },
                    "items": [
                        {
                            "id": "folder-item-1",
                            "label": "Specific Heat",
                            "metadata": {
                                "folder_item_id": "folder-item-1",
                                "folder_name": "Thermodynamics",
                                "quiz_id": "quiz-1",
                                "title": "Specific Heat",
                                "display_title": "Specific Heat",
                                "question_type": "multichoice",
                            },
                        }
                    ],
                },
            }
        ],
    )

    assert artifacts[0].data["title"] == "Answer Key: Specific Heat"
    assert artifacts[0].data["metadata"]["title"] == "Specific Heat"
    assert artifacts[0].data["metadata"]["canonical_title"] == "Physics"
    assert artifacts[0].data["metadata"]["quiz_id"] == "quiz-1"


def test_folder_artifact_keeps_canonical_folder_name_separate_from_display_title():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="folder_get_by_name",
                data={
                    "found": True,
                    "folder_id": "folder-1",
                    "id": "folder-1",
                    "name": "Thermodynamics",
                    "quizzes": [
                        {
                            "id": "folder-item-1",
                            "quiz_id": "quiz-1",
                            "title": "Specific Heat",
                            "question_type": "multichoice",
                        }
                    ],
                },
            )
        ]
    )

    assert artifacts[0].data["title"] == "Thermodynamics Folder"
    assert artifacts[0].data["metadata"]["folder_name"] == "Thermodynamics"
    assert artifacts[0].data["items"][0]["metadata"]["folder_name"] == "Thermodynamics"


def test_folder_artifact_does_not_double_suffix_folder_display_title():
    artifacts = infer_artifacts_from_results(
        [
            ToolResult(
                step_id="step_1",
                tool_name="folder_get_by_name",
                data={
                    "found": True,
                    "folder_id": "folder-1",
                    "id": "folder-1",
                    "name": "Thermodynamics Folder",
                    "quizzes": [],
                },
            )
        ]
    )

    assert artifacts[0].data["title"] == "Thermodynamics Folder"
    assert artifacts[0].data["metadata"]["folder_name"] == "Thermodynamics Folder"
