import pytest

import pytest_asyncio

from httpx import AsyncClient

from httpx._transports.asgi import ASGITransport

from ...main import app

from ...app.db.routes import users







@pytest_asyncio.fixture(scope="function")

def sample_user():

    return {

        "username": "testuser",

        "email": "testuser@example.com",

        "password": "Secure123!",

        "full_name": "Test User"

    }



@pytest_asyncio.fixture(scope="function")

def updated_user():

    return {

        "username": "updateduser",

        "email": "updateduser@example.com",

        "password": "Newsecure123!",

        "full_name": "Updated User"

    }



@pytest_asyncio.fixture(scope="function")

async def client(seeded_database):

    test_users_collection = seeded_database["users"]

    app.dependency_overrides[users.get_users_collection] = lambda: test_users_collection

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:

        yield c



@pytest_asyncio.fixture(scope="function")

async def created_user(client, sample_user):

    response = await client.post("/users/test/create-user", json=sample_user)

    return response.json()




@pytest.mark.asyncio

async def test_create_user_endpoint(client, sample_user):

    response = await client.post("/users/test/create-user", json=sample_user)


    assert response.status_code == 200

    data = response.json()

    assert data["email"] == sample_user["email"]

    assert data["username"] == sample_user["username"]

    assert "id" in data

    assert "password" not in data



@pytest.mark.asyncio

async def test_get_user_by_id_endpoint(client, created_user):

    user_id = created_user["id"]

    response = await client.get(f"/users/test/get-user/{user_id}")


    assert response.status_code == 200

    data = response.json()

    assert data["id"] == user_id

    for field in ("username", "email", "role", "created_at", "quizzes"):

        assert field in data



@pytest.mark.asyncio

async def test_get_user_by_email_endpoint(client, created_user):

    email = created_user["email"]

    response = await client.get(f"/users/test/get-user-by-email/{email}")


    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email

    for field in ("username", "id", "role", "created_at", "quizzes"):

        assert field in data



@pytest.mark.asyncio

async def test_update_user_endpoint(client, created_user, updated_user):

    user_id = created_user["id"]

    response = await client.put(f"/users/test/update-user/{user_id}", json=updated_user)


    assert response.status_code == 200

    data = response.json()

    assert data["username"] == updated_user["username"]

    assert data["email"] == updated_user["email"]

    assert data["full_name"] == updated_user["full_name"]

    assert "id" in data

    assert data.get("updated_at") is not None



@pytest.mark.asyncio

async def test_list_users_endpoint(client):

    response = await client.get("/users/test/list-users")


    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    expected_values = [

        ("username", "mike_johnson"),

        ("email", "john.doe@example.com"),

        ("full_name", "Emily Adams"),

    ]

    for key, val in expected_values:

        assert any(user.get(key) == val for user in data)



@pytest.mark.asyncio

async def test_delete_user_endpoint(client, created_user):

    user_id = created_user["id"]

    response = await client.delete(f"/users/test/delete-user/{user_id}")


    assert response.status_code == 200

    data = response.json()

    assert f"User with ID {user_id} deleted successfully" in data["message"]

    assert data["delete_count"] > 0



@pytest.mark.asyncio

async def test_login_endpoint(client, created_user, sample_user):

    login_data = {

        "username": created_user["username"],

        "email": created_user["email"],

        "password": sample_user["password"]

    }

    response = await client.post("/users/test/login/", json=login_data)


    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Login successful"

    assert data["username"] == created_user["username"]

    for key in ("user_id", "role"):

        assert key in data

    assert "password" not in data



@pytest.mark.asyncio

async def test_login_invalid_credentials(client):

    login_data = {

        "username": "nonexistent",

        "email": "wrong@email.com",

        "password": "Wrongpass1!"

    }

    response = await client.post("/users/test/login/", json=login_data)


    assert response.status_code == 401



@pytest.mark.asyncio

async def test_create_user_missing_email(client):

    user_data = {

        "username": "incomplete",

        "password": "Pass1234!",

        "full_name": "Incomplete User"

    }

    response = await client.post("/users/test/create-user", json=user_data)


    assert response.status_code == 422



@pytest.mark.asyncio

async def test_get_nonexistent_user(client):

    response = await client.get("/users/test/get-user/nonexistentid123")


    assert response.status_code in [404, 400]



@pytest.mark.asyncio

@pytest.mark.parametrize("login_data", [

    {"username": "david_clark", "email": "david.clark@example.com", "password": "Wrongpass1!"},

    {"username": "nonexistent", "email": "nonexistent@example.com", "password": "Testpassword8!"},

])

async def test_login_fails_various(client, login_data):

    response = await client.post("/users/test/login/", json=login_data)


    assert response.status_code == 401



@pytest.mark.asyncio

async def test_user_deletion_removes_user(client, created_user):

    user_id = created_user["id"]

    await client.delete(f"/users/test/delete-user/{user_id}")

    response = await client.get(f"/users/test/get-user/{user_id}")


    assert response.status_code in [404, 400]



@pytest.mark.asyncio

async def test_list_users_empty(client, seeded_database):

    await seeded_database["users"].drop()

    response = await client.get("/users/test/list-users")


    assert response.status_code == 200

    assert response.json() == []
