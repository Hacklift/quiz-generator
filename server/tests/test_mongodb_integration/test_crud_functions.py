import pytest

import pytest_asyncio

from ...app.db.crud.user_crud import (

    create_user,

    get_user_by_id,

    get_user_by_email,

    update_user,

    delete_user,

    list_users)

from ...app.db.crud.quiz_crud import (

    create_quiz,

    get_quiz,

    update_quiz,

    delete_quiz

)

from ...app.db.schemas.user_schemas import (

    CreateUserRequest,

    UpdateUserSchema,

)

from ...app.db.schemas.quiz_schemas import (

    NewQuizSchema,

    UpdateQuiz

)





@pytest_asyncio.fixture(scope="function")

def sample_user_data():

    return CreateUserRequest(

        username="testuser",

        email="testuser@example.com",

        password="testpass123",

        full_name="Test User"

    )


@pytest_asyncio.fixture(scope="function")

def update_user_data():

    return UpdateUserSchema(

        username="updatedTestUser",

        email="updatedTestUser@example.com",

        password="updatedTestPass123",

        full_name="Updated Test User"

    )


@pytest_asyncio.fixture(scope="function")

async def new_user(test_db, sample_user_data):

    new_user = await create_user(test_db["users"], sample_user_data)

    return new_user



@pytest_asyncio.fixture(scope="function")

async def sample_quiz_data():

    return NewQuizSchema(

        title="test quiz title",

        description="test quiz description",

        quiz_type="true-false",

        questions=[

            {

            "question": "There are seven continents on Earth.",

            "options": ["True", "False"],

            "correct_answer": "True"

        },

        {

            "question": "Pluto is still classified as a planet.",

            "options": ["True", "False"],

            "correct_answer": "False"

        }

        ]

    )


@pytest_asyncio.fixture(scope="function")

async def update_sample_quiz_data():

    return UpdateQuiz(

        title="updated test quiz title",

        description="updated test quiz description",

        quiz_type="true-false",

        questions=[

             {

            "question": "Crop rotation helps to prevent soil depletion.",

            "options": ["True", "False"],

            "correct_answer": "True"

        },

        {

            "question": "Drones are used in modern agriculture for crop monitoring.",

            "options": ["True", "False"],

            "correct_answer": "True"

        }

        ]

    )


@pytest_asyncio.fixture(scope="function")

async def new_quiz(test_db, sample_quiz_data):

    new_quiz = await create_quiz(test_db["quizzes"], sample_quiz_data)

    return new_quiz.id






@pytest.mark.asyncio

async def test_create_user(test_db, sample_user_data):


    new_user = await create_user(test_db["users"], sample_user_data)


    assert new_user is not None

    assert new_user.username == sample_user_data.username

    assert new_user.email == sample_user_data.email

    assert new_user.id is not None



@pytest.mark.asyncio

async def test_get_user_by_id(test_db, new_user, sample_user_data):

    user_id = new_user.id

    user = await get_user_by_id(test_db["users"], user_id)


    assert user is not None

    assert user.id == user_id

    assert user.username == sample_user_data.username

    assert user.email == sample_user_data.email

    assert user.full_name == sample_user_data.full_name

    assert user.role is not None

    assert user.quizzes is not None

    assert user.created_at is not None



@pytest.mark.asyncio

async def test_get_user_by_email(test_db, new_user, sample_user_data):

    user_email = new_user.email

    user = await get_user_by_email(test_db["users"], user_email)


    assert user is not None

    assert user.username == sample_user_data.username

    assert user.email == sample_user_data.email

    assert user.full_name == sample_user_data.full_name

    assert user.role is not None

    assert user.quizzes is not None

    assert user.created_at is not None



@pytest.mark.asyncio

async def test_update_user(test_db, new_user, update_user_data):

    user_id = new_user.id

    updated_user = await update_user(test_db["users"], user_id, update_user_data)


    assert updated_user is not None

    assert updated_user.updated_at is not None

    assert updated_user.username == update_user_data.username

    assert updated_user.email == update_user_data.email

    assert updated_user.full_name == update_user_data.full_name

    assert updated_user.role is not None

    assert updated_user.quizzes is not None

    assert updated_user.created_at is not None




@pytest.mark.asyncio

async def test_delete_user(test_db, new_user):

    user_id = new_user.id

    response = await delete_user(test_db["users"], user_id)


    assert response is not None

    assert response.message == f"User with ID {user_id} deleted successfully"

    assert response.delete_count > 0



@pytest.mark.asyncio

async def test_list_users(seeded_database):

    users = await list_users(seeded_database["users"])


    assert isinstance(users, list)

    assert any(user.username == "jane_smith" for user in users)

    assert any(user.email == "alex.walker@example.com" for user in users)

    assert any(user.full_name == "Lisa Martin" for user in users)

    assert len(users) > 8




@pytest.mark.asyncio

async def test_create_quiz(test_db, sample_quiz_data):

    new_quiz = await create_quiz(test_db["quizzes"], sample_quiz_data)


    assert new_quiz.id is not None

    assert new_quiz.title == sample_quiz_data.title

    assert new_quiz.description == sample_quiz_data.description



@pytest.mark.asyncio

async def test_get_quiz(test_db, new_quiz):

    quiz_id = new_quiz

    quiz = await get_quiz(test_db["quizzes"], quiz_id)


    assert quiz is not None

    assert quiz.created_at is not None

    assert quiz.questions is not None

    assert quiz.title == "test quiz title"

    assert quiz.description == "test quiz description"

    assert quiz.quiz_type == "true-false"



@pytest.mark.asyncio

async def test_update_quiz(test_db, update_sample_quiz_data, new_quiz):

    quiz_id = new_quiz

    updated_quiz = await update_quiz(test_db["quizzes"], quiz_id, update_sample_quiz_data)


    assert updated_quiz is not None

    assert updated_quiz.updated_at is not None

    assert updated_quiz.title == update_sample_quiz_data.title

    assert updated_quiz.description == update_sample_quiz_data.description



@pytest.mark.asyncio

async def test_delete_quiz(test_db, new_quiz):

    quiz_id = new_quiz

    response = await delete_quiz(test_db["quizzes"], quiz_id)


    assert response.message == f"Quiz with ID {quiz_id} deleted successfully"

    assert response.delete_count > 0



@pytest.mark.asyncio

async def test_list_quizzes(seeded_database):

    quizzes_cursor = seeded_database["quizzes"].find({})

    quizzes = await quizzes_cursor.to_list()


    assert any(quiz["description"] == "Assess your understanding of agricultural practices and food production." for quiz in quizzes)

    assert any(quiz["questions"][0]["question"] == "Who was the first President of the United States?" for quiz in quizzes)

    assert any(quiz["questions"][0]["correct_answer"] == "George Washington" for quiz in quizzes)


