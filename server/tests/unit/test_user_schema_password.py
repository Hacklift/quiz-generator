import pytest
from pydantic import ValidationError
from server.app.db.schemas.user_schemas import UserRegisterSchema


def test_user_register_schema_accepts_valid_password():
    user = UserRegisterSchema(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="Abcd1234!",
    )
    assert user.username == "testuser"


def test_user_register_schema_rejects_password_missing_uppercase():
    with pytest.raises(ValidationError):
        UserRegisterSchema(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="abcd1234!",
        )


def test_user_register_schema_rejects_password_missing_lowercase():
    with pytest.raises(ValidationError):
        UserRegisterSchema(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="ABCD1234!",
        )


def test_user_register_schema_rejects_password_missing_number():
    with pytest.raises(ValidationError):
        UserRegisterSchema(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="Abcdabcd!",
        )


def test_user_register_schema_rejects_password_missing_special():
    with pytest.raises(ValidationError):
        UserRegisterSchema(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="Abcd1234",
        )


def test_user_register_schema_rejects_short_password():
    with pytest.raises(ValidationError):
        UserRegisterSchema(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="Ab1!",
        )
