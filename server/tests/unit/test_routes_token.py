import pytest

from server.app.db.routes import token_router


@pytest.mark.asyncio
async def test_token_routes(monkeypatch, dummy_user):
  async def fake_save_user_token(_user_id, _token):
    return None

  async def fake_get_user_token(_user_id):
    return "abc"

  monkeypatch.setattr(token_router, "save_user_token", fake_save_user_token)
  monkeypatch.setattr(token_router, "get_user_token", fake_get_user_token)

  res = await token_router.add_token(token_router.TokenIn(token="abc"), user=dummy_user)
  assert res["message"] == "Token saved successfully"

  fetched = await token_router.fetch_token(user=dummy_user)
  assert fetched["token"] == "abc"
