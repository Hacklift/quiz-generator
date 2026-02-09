import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from unittest.mock import AsyncMock
from server.app.db.routes import folder_routes


@pytest.mark.asyncio
async def test_create_folder_success(monkeypatch):
    async def fake_create_folder(data):
        return {"_id": "f1", **data}

    monkeypatch.setattr(folder_routes, "create_folder", fake_create_folder)

    folder = folder_routes.FolderCreate(name="My Folder")
    user = SimpleNamespace(id="user1")

    result = await folder_routes.create_new_folder(folder, user=user)

    assert result["folder"]["name"] == "My Folder"


@pytest.mark.asyncio
async def test_create_folder_duplicate_returns_error(monkeypatch):
    async def fake_create_folder(_data):
        raise HTTPException(status_code=400, detail="Folder already exists")

    monkeypatch.setattr(folder_routes, "create_folder", fake_create_folder)

    folder = folder_routes.FolderCreate(name="My Folder")
    user = SimpleNamespace(id="user1")

    with pytest.raises(HTTPException) as exc:
        await folder_routes.create_new_folder(folder, user=user)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_quiz_to_folder_success(monkeypatch):
    async def fake_get_folder_by_id(_folder_id):
        return {"_id": "f1", "user_id": "user1"}

    async def fake_add_quiz_to_folder(_folder_id, quiz):
        return {"_id": "f1", "quizzes": [quiz]}

    monkeypatch.setattr(folder_routes, "get_folder_by_id", fake_get_folder_by_id)
    monkeypatch.setattr(folder_routes, "add_quiz_to_folder", fake_add_quiz_to_folder)

    mock_saved = AsyncMock()
    quiz_id = "507f1f77bcf86cd799439011"
    mock_saved.find_one.return_value = {
        "_id": quiz_id,
        "title": "Quiz",
        "questions": [],
    }
    monkeypatch.setattr(folder_routes, "saved_quizzes_collection", mock_saved)

    user = SimpleNamespace(id="user1")
    quiz = folder_routes.QuizData(quiz_id=quiz_id, title="Quiz", quiz_data={})

    result = await folder_routes.add_quiz_to_folder_route("f1", quiz, user=user)

    assert result["message"].startswith("Quiz added")
