import pytest
from starlette.requests import Request

pytest.importorskip("slowapi")
from server.app.db.core.rate_limiter import get_rate_limit_key


def make_request(headers=None, user=None):
  scope = {"type": "http", "headers": []}
  req = Request(scope)
  if headers:
    req.scope["headers"] = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
  req.state.user = user
  return req


def test_rate_limit_key_user():
  req = make_request(user=type("U", (), {"id": "u1"})())
  assert get_rate_limit_key(req) == "user:u1"


def test_rate_limit_key_token():
  req = make_request(headers={"Authorization": "Bearer abc"})
  assert get_rate_limit_key(req).startswith("token:")


def test_rate_limit_key_ip_fallback():
  req = make_request()
  assert get_rate_limit_key(req).startswith("ip:")
