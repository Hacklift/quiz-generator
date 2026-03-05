import pytest

from server.app.db.crud import folder_crud as fc


@pytest.mark.asyncio
async def test_create_and_get_folder(monkeypatch, fake_folders_collection):
  monkeypatch.setattr(fc, "folders_collection", fake_folders_collection)
  folder = await fc.create_folder({"name": "Test", "user_id": "u1", "quizzes": []})
  assert folder["name"] == "Test"
  fetched = await fc.get_folder_by_id(folder["_id"])
  assert fetched["name"] == "Test"


@pytest.mark.asyncio
async def test_add_and_remove_quiz(monkeypatch, fake_folders_collection):
  monkeypatch.setattr(fc, "folders_collection", fake_folders_collection)
  folder = await fc.create_folder({"name": "Test", "user_id": "u1", "quizzes": []})
  updated = await fc.add_quiz_to_folder(folder["_id"], {"title": "Q"})
  assert len(updated["quizzes"]) == 1
  quiz_id = updated["quizzes"][0]["_id"]
  updated = await fc.remove_quiz_from_folder(folder["_id"], quiz_id)
  assert len(updated["quizzes"]) == 0
