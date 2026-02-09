import importlib
import pytest
from unittest.mock import AsyncMock
from cryptography.fernet import Fernet


@pytest.mark.asyncio
async def test_save_and_get_user_token(monkeypatch):
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    importlib.reload(importlib.import_module("server.app.db.core.connection"))
    token_crud = importlib.reload(importlib.import_module("server.app.db.crud.token_crud"))

    collection = AsyncMock()
    monkeypatch.setattr(token_crud, "get_user_tokens_collection", lambda: collection)

    token = "api-token"
    user_id = "user1"

    await token_crud.save_user_token(user_id, token)

    assert collection.update_one.await_count == 1

    encrypted = collection.update_one.call_args[0][1]["$set"]["token"]
    collection.find_one.return_value = {"user_id": user_id, "token": encrypted}

    result = await token_crud.get_user_token(user_id)

    assert result == token
