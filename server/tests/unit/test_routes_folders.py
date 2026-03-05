import pytest
from bson import ObjectId

from server.app.db.routes import folder_routes
from server.app.db.models.folder_model import FolderCreate


@pytest.mark.asyncio
async def test_folder_routes(monkeypatch, dummy_user):
  folder_id = str(ObjectId())
  quiz_id = str(ObjectId())

  async def fake_create_folder(_data):
    return {"_id": folder_id, "user_id": dummy_user.id, "name": "F"}

  async def fake_get_user_folders(_user_id):
    return [{"_id": folder_id, "user_id": dummy_user.id, "name": "F"}]

  async def fake_get_folder_by_id(_fid):
    return {"_id": folder_id, "user_id": dummy_user.id, "quizzes": []}

  async def fake_add_quiz_to_folder(_fid, _quiz_entry):
    return {"_id": folder_id, "user_id": dummy_user.id, "quizzes": [{"_id": quiz_id}]}

  monkeypatch.setattr(folder_routes, "create_folder", fake_create_folder)
  monkeypatch.setattr(folder_routes, "get_user_folders", fake_get_user_folders)
  monkeypatch.setattr(folder_routes, "get_folder_by_id", fake_get_folder_by_id)
  monkeypatch.setattr(folder_routes, "add_quiz_to_folder", fake_add_quiz_to_folder)

  class FakeSavedQuizzes:
    async def find_one(self, *_args, **_kwargs):
      return {"_id": ObjectId(quiz_id), "title": "Quiz", "question_type": "multichoice", "questions": []}

  monkeypatch.setattr(folder_routes, "saved_quizzes_collection", FakeSavedQuizzes())

  created = await folder_routes.create_new_folder(FolderCreate(name="F"), user=dummy_user)
  assert created["message"] == "Folder created successfully"

  folders = await folder_routes.get_folders_for_user(user=dummy_user)
  assert len(folders) == 1

  added = await folder_routes.add_quiz_to_folder_route(folder_id, folder_routes.QuizData(quiz_id=quiz_id), user=dummy_user)
  assert added["message"] == "Quiz added to folder successfully"
