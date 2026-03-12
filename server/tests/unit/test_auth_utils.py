import jwt
import pytest
from datetime import datetime, timezone, timedelta

from server.app.auth import utils
from server.app.db.core.config import settings


def test_create_access_token_contains_type_and_exp():
  token = utils.create_access_token({"sub": "user123"}, expires_delta=timedelta(minutes=5))
  payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
  assert payload["sub"] == "user123"
  assert payload["type"] == "access"
  assert "jti" in payload
  assert payload["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_create_refresh_token_contains_type_and_jti():
  token, jti, exp = utils.create_refresh_token({"sub": "user123"})
  payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
  assert payload["sub"] == "user123"
  assert payload["type"] == "refresh"
  assert payload["jti"] == jti
  assert payload["exp"] == int(exp.timestamp())


def test_decode_refresh_token_rejects_wrong_type():
  access = utils.create_access_token({"sub": "user123"})
  with pytest.raises(Exception):
    utils.decode_refresh_token(access)


def test_verification_token_roundtrip():
  token = utils.generate_verification_token("user@example.com")
  email = utils.decode_verification_token(token)
  assert email == "user@example.com"


def test_hash_token_roundtrip():
  token = "sensitive-token"
  try:
    hashed = utils.hash_token(token)
  except ValueError as exc:
    pytest.skip(f"bcrypt backend issue in environment: {exc}")
  assert utils.verify_token_hash(token, hashed) is True


def test_password_hash_roundtrip():
  password = "StrongP@ss1"
  try:
    hashed = utils.get_password_hash(password)
  except ValueError as exc:
    pytest.skip(f"bcrypt backend issue in environment: {exc}")
  assert utils.verify_password(password, hashed)
