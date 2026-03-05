import pytest

from server.app.db.crud import token_crud


@pytest.mark.asyncio
async def test_save_and_get_user_token(monkeypatch, fake_user_tokens_collection):
  monkeypatch.setattr(token_crud, "get_user_tokens_collection", lambda: fake_user_tokens_collection)

  await token_crud.save_user_token("user1", "secret-token")
  token = await token_crud.get_user_token("user1")
  assert token == "secret-token"
