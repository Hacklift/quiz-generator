import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytest.importorskip("slowapi")
from server.app.auth import routes as auth_routes


def test_auth_login_and_refresh(monkeypatch):
  async def fake_login_service(*_args, **_kwargs):
    return {"message": "Login successful", "access_token": "a", "refresh_token": "r", "token_type": "bearer"}

  async def fake_refresh_service(*_args, **_kwargs):
    return {"access_token": "a2", "refresh_token": "r2", "token_type": "bearer"}

  monkeypatch.setattr(auth_routes, "login_service", fake_login_service)
  monkeypatch.setattr(auth_routes, "refresh_token_service", fake_refresh_service)

  app = FastAPI()
  app.include_router(auth_routes.router, prefix="/auth")
  client = TestClient(app)

  res = client.post("/auth/login", json={"identifier": "u", "password": "p"})
  assert res.status_code == 200
  res = client.post("/auth/refresh", json={"refresh_token": "r"})
  assert res.status_code == 200
