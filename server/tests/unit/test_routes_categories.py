import pytest

from server.app.db.routes import get_categories


@pytest.mark.asyncio
async def test_get_categories_routes(monkeypatch):
  class FakeCategories:
    async def distinct(self, field, *_args, **_kwargs):
      if field == "category":
        return ["Science"]
      if field == "subcategory":
        return ["Physics"]
      return ["multichoice"]

    def find(self, *_args, **_kwargs):
      class Cursor:
        def skip(self, _n):
          return self

        def limit(self, _n):
          return self

        async def to_list(self, length=None):
          return [
            {
              "subcategory": "Physics",
              "question_type": "multichoice",
              "questions": [{"question": "Q", "answer": "A", "options": []}],
            }
          ]

      return Cursor()

  monkeypatch.setattr(get_categories, "quiz_categories_collection", FakeCategories())

  categories = await get_categories.get_categories()
  assert categories == ["Science"]

  subcategories = await get_categories.get_subcategories("Science")
  assert subcategories == ["Physics"]

  quiz_types = await get_categories.get_quiz_types("Science", "Physics")
  assert quiz_types == ["multichoice"]

  quizzes = await get_categories.get_quizzes_by_category_subcategory_type(
    "Science",
    "Physics",
    "multichoice",
    page=1,
    page_size=5,
  )
  assert len(quizzes) == 1
