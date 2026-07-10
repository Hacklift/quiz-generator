import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")
os.environ.setdefault("ASSISTANT_INTERNAL_MCP_SECRET", "test-internal-mcp-secret")

from server.app.assistant.tool_policy import get_tool_definition
from server.app.core.config import settings
from server.app.quiz.services.generation_policy import validate_generation_question_count


def test_generation_question_count_accepts_configured_maximum():
    assert validate_generation_question_count(settings.QUIZ_GENERATION_MAX_QUESTIONS) == settings.QUIZ_GENERATION_MAX_QUESTIONS


def test_generation_question_count_rejects_values_above_configured_maximum():
    with pytest.raises(HTTPException) as exc:
        validate_generation_question_count(settings.QUIZ_GENERATION_MAX_QUESTIONS + 1)

    assert exc.value.status_code == 422
    assert str(settings.QUIZ_GENERATION_MAX_QUESTIONS) in exc.value.detail


def test_quiz_generate_tool_requires_authenticated_verified_user():
    definition = get_tool_definition("quiz_generate")

    assert definition.requires_auth is True
    assert definition.requires_verified is True
    assert definition.argument_schema["num_questions"]["maximum"] == settings.QUIZ_GENERATION_MAX_QUESTIONS
