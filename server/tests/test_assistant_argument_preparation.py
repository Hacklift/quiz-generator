import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")

from server.app.assistant.argument_preparation import PreparationStatus, StepPreparationPipeline
from server.app.assistant.schemas import ToolResult
from server.app.assistant.tool_policy import get_tool_definition
from server.app.assistant.resource_resolver import AssistantResourceResolver, ResourceResolutionStatus


def test_required_arguments_come_from_tool_contract():
    contract = get_tool_definition("folder_move_quiz")

    assert contract.required_arguments == (
        "folder_item_id",
        "source_folder_id",
        "target_folder_id",
    )


def test_preparation_resolves_previous_result_with_provenance():
    result = StepPreparationPipeline().prepare(
        tool_name="folder_add_saved_quiz",
        arguments={
            "folder_id": "$steps.step_1.result.folder_id",
            "saved_quiz_id": "$steps.step_2.result.saved_quiz_id",
        },
        previous_results=[
            ToolResult(
                step_id="step_1",
                tool_name="folder_create",
                data={"folder_id": "folder-1"},
            ),
            ToolResult(
                step_id="step_2",
                tool_name="library_save_quiz",
                data={"saved_quiz_id": "saved-1"},
            ),
        ],
        user_id="user-1",
    )

    assert result.status is PreparationStatus.READY
    assert result.arguments == {"folder_id": "folder-1", "saved_quiz_id": "saved-1"}
    assert result.provenance == {
        "folder_id": "tool_result:step_1",
        "saved_quiz_id": "tool_result:step_2",
    }


def test_unresolved_reference_is_ambiguous_not_missing():
    result = StepPreparationPipeline().prepare(
        tool_name="folder_add_saved_quiz",
        arguments={
            "folder_id": "$steps.step_1.result.folder_id",
            "saved_quiz_id": "saved-1",
        },
        previous_results=[],
        user_id="user-1",
    )

    assert result.status is PreparationStatus.AMBIGUOUS
    assert result.needs_model_assistance is True
    assert result.problems[0].field == "folder_id"


def test_absent_required_value_is_missing_and_does_not_request_model():
    result = StepPreparationPipeline().prepare(
        tool_name="folder_create",
        arguments={},
        previous_results=[],
        user_id="user-1",
    )

    assert result.status is PreparationStatus.MISSING
    assert result.missing_fields == ["name"]
    assert result.needs_model_assistance is False


def test_invalid_enum_is_reported_without_model_assistance():
    result = StepPreparationPipeline().prepare(
        tool_name="quiz_export_link",
        arguments={"quiz_id": "quiz-1", "format": "xlsx"},
        previous_results=[],
        user_id="user-1",
    )

    assert result.status is PreparationStatus.INVALID
    assert result.problems[0].code == "invalid_value"


def test_library_save_accepts_canonical_quiz_id_without_payload():
    result = StepPreparationPipeline().prepare(
        tool_name="library_save_quiz",
        arguments={"quiz_id": "quiz-1"},
        previous_results=[],
        user_id="user-1",
    )

    assert result.status is PreparationStatus.READY


def test_resource_resolver_reports_close_candidates_as_ambiguous():
    resolution = AssistantResourceResolver().resolve_quiz_result(
        message="Open Database Indexing",
        recent_artifacts=[
            {
                "type": "resource_list",
                "data": {
                    "resource": "saved_quiz",
                    "items": [
                        {"id": "saved-1", "label": "Database Indexing", "metadata": {"quiz_id": "quiz-1"}},
                        {"id": "saved-2", "label": "Database Indexing", "metadata": {"quiz_id": "quiz-2"}},
                    ],
                },
            }
        ],
    )

    assert resolution.status is ResourceResolutionStatus.AMBIGUOUS
    assert len(resolution.candidates) == 2
