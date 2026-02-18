import pytest

import pytest_asyncio

from httpx import AsyncClient

from httpx._transports.asgi import ASGITransport

from ...main import app

from ...app.db.routes import quizzes




@pytest_asyncio.fixture(scope="function")

def sample_quiz():

    return {

        "title": "Sample Quiz",

        "description": "A simple quiz for testing",

        "quiz_type": "multichoice",

        "questions": [

            {

                "question": "What is the capital of France?",

                "options": ["Paris", "Rome", "Berlin", "Madrid"],

                "answer": "Paris"

            },

            {

                "question": "What is 2 + 2?",

                "options": ["3", "4", "5", "6"],

                "answer": "4"

            }

        ],

    }



@pytest_asyncio.fixture(scope="function")

def updated_quiz():

    return {

        "title": "Updated Quiz",

        "description": "An updated quiz for testing",

        "quiz_type": "multichoice",

        "questions": [

            {

                "question": "What is the capital of Italy?",

                "options": ["Rome", "Paris", "Berlin", "Madrid"],

                "answer": "Rome"

            },

            {

            "question": "Humans first landed on the Moon in 1969.",

            "options": ["True", "False"],

            "correct_answer": "True"

            }

        ],

    }



@pytest_asyncio.fixture(scope="function")

async def client(seeded_database):

    test_quizzes_collection = seeded_database["quizzes"]

    app.dependency_overrides[quizzes.get_quizzes_collection] = lambda: test_quizzes_collection

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:

        yield c



@pytest_asyncio.fixture(scope="function")

async def created_quiz(client, sample_quiz):

    response = await client.post("/quizzes/test/create-quiz", json=sample_quiz)

    return response.json()



@pytest.mark.asyncio

async def test_create_quiz_endpoint(client, sample_quiz):

    response = await client.post("/quizzes/test/create-quiz", json=sample_quiz)


    assert response.status_code == 200

    data = response.json()

    assert data["title"] == sample_quiz["title"]

    assert data["description"] == sample_quiz["description"]

    assert "id" in data



@pytest.mark.asyncio

async def test_get_quiz_by_id_endpoint(client, created_quiz):

    quiz_id = created_quiz["id"]

    response = await client.get(f"/quizzes/test/get-quiz/{quiz_id}")


    assert response.status_code == 200

    data = response.json()

    assert data["id"] == quiz_id

    assert data["title"] == created_quiz["title"]

    assert isinstance(data["questions"], list)



@pytest.mark.asyncio

async def test_update_quiz_endpoint(client, created_quiz, updated_quiz):

    quiz_id = created_quiz["id"]

    response = await client.put(f"/quizzes/test/update-quiz/{quiz_id}", json=updated_quiz)


    assert response.status_code == 200

    data = response.json()

    assert data["title"] == updated_quiz["title"]

    assert data["description"] == updated_quiz["description"]

    assert len(data["questions"]) == 2



@pytest.mark.asyncio

async def test_delete_quiz_endpoint(client, created_quiz):

    quiz_id = created_quiz["id"]

    response = await client.delete(f"/quizzes/test/delete-quiz/{quiz_id}")


    assert response.status_code == 200

    data = response.json()

    assert f"Quiz with ID {quiz_id} deleted successfully" in data["message"]

    assert data["delete_count"] > 0



@pytest.mark.asyncio

async def test_get_nonexistent_quiz(client):

    response = await client.get("/quizzes/test/get-quiz/nonexistentid123")


    assert response.status_code == 404



@pytest.mark.asyncio

async def test_update_nonexistent_quiz(client, updated_quiz):

    response = await client.put("/quizzes/test/update-quiz/nonexistentid123", json=updated_quiz)


    assert response.status_code == 404



@pytest.mark.asyncio

async def test_delete_nonexistent_quiz(client):

    response = await client.delete("/quizzes/test/delete-quiz/nonexistentid123")


    assert response.status_code == 404

