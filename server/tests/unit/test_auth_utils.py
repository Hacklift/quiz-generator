import pytest
import jwt
from datetime import timedelta
from server.app.auth import utils
from server.app.db.core.config import settings


def setup_module(module):
    settings.JWT_SECRET = "testsecret"
    settings.JWT_ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 5
    settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
    settings.VERIFICATION_TOKEN_EXPIRE_HOURS = 2


def test_generate_otp_returns_six_digits():
    otp = utils.generate_otp()
    assert otp.isdigit()
    assert len(otp) == 6


def test_create_access_token_and_decode():
    token = utils.create_access_token({"sub": "user@example.com"}, expires_delta=timedelta(minutes=1))
    decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "user@example.com"
    assert "exp" in decoded


def test_create_refresh_token_and_decode():
    token, jti, exp = utils.create_refresh_token({"sub": "user@example.com"})
    decoded = utils.decode_refresh_token(token)
    assert decoded["sub"] == "user@example.com"
    assert decoded["type"] == "refresh"
    assert decoded["jti"] == jti
    assert exp is not None


def test_decode_refresh_token_rejects_non_refresh():
    access_token = utils.create_access_token({"sub": "user@example.com"})
    with pytest.raises(Exception):
        utils.decode_refresh_token(access_token)


def test_hash_and_verify_token(monkeypatch):
    token = "token123"
    monkeypatch.setattr(utils.pwd_context, "hash", lambda _t: "hashed")
    monkeypatch.setattr(utils.pwd_context, "verify", lambda t, h: t == "token123" and h == "hashed")
    hashed = utils.hash_token(token)
    assert utils.verify_token_hash(token, hashed) is True
    assert utils.verify_token_hash("wrong", hashed) is False
