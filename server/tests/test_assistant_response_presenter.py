import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")

from server.app.assistant.outcomes import project_tool_outcomes
from server.app.assistant.confirmation_presenter import ConfirmationPresenter
from server.app.assistant.response_presenter import AssistantResponsePresenter, outcome_artifact_label
from server.app.assistant.schemas import ToolResult


def _result(step_id: str, tool_name: str, **data):
    return ToolResult(step_id=step_id, tool_name=tool_name, data=data)


def test_compound_summary_includes_every_successful_user_action():
    results = [
        _result("step_1", "quiz_generate", quiz_id="quiz-1", title="Database Indexing"),
        _result("step_2", "library_save_quiz", quiz_id="quiz-1", title="Database Indexing"),
        _result(
            "step_3",
            "folder_add_saved_quiz",
            quiz_id="quiz-1",
            title="Database Indexing",
            folder_name="Software Engineering",
        ),
        _result("step_4", "share_create_link", quiz_id="quiz-1", link="https://example.test/share/quiz-1"),
        _result(
            "step_5",
            "share_send_email",
            quiz_id="quiz-1",
            recipient_email="user@example.com",
            message="Email sent successfully.",
        ),
    ]

    response = AssistantResponsePresenter().present(results)

    assert response is not None
    assert "generated Database Indexing" in response.message
    assert response.message == (
        "I generated Database Indexing, saved it, added it to Software Engineering, "
        "created a share link for it, and sent it to user@example.com."
    )


def test_status_artifact_label_and_summary_share_the_same_outcome():
    results = [
        _result(
            "step_1",
            "share_send_email",
            quiz_id="quiz-1",
            recipient_email="user@example.com",
            message="Email sent successfully.",
        )
    ]

    outcome = project_tool_outcomes(results)[0]
    response = AssistantResponsePresenter().present(results)

    assert outcome_artifact_label(outcome) == "Share link sent to user@example.com."
    assert response is not None
    assert response.message == "I sent this quiz link to user@example.com."


def test_confirmation_resolves_generated_quiz_title_from_canonical_id():
    results = [_result("step_1", "quiz_generate", quiz_id="quiz-1", title="Arduino microcontrollers")]

    message = ConfirmationPresenter().message(
        tool_name="library_save_quiz",
        arguments={"quiz_id": "quiz-1"},
        results=results,
        page_context=None,
        recent_artifacts=None,
    )

    assert message == "Please confirm: save Arduino microcontrollers to your library."


def test_share_confirmation_resolves_title_from_recent_artifact():
    message = ConfirmationPresenter().message(
        tool_name="share_send_email",
        arguments={"quiz_id": "quiz-1", "recipient_email": "user@example.com"},
        results=[],
        page_context=None,
        recent_artifacts=[
            {
                "type": "resource",
                "data": {
                    "resource": "quiz",
                    "metadata": {"quiz_id": "quiz-1", "title": "Arduino microcontrollers"},
                },
            }
        ],
    )

    assert message == (
        "Please confirm: send the Arduino microcontrollers quiz link to user@example.com."
    )
