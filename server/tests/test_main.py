import pytest


pytest.skip(

    "Legacy tests for a removed app.main module; skipping.",

    allow_module_level=True,

)


from fastapi.testclient import TestClient

from app.main import app, User, mock_db

from fastapi import HTTPException


client = TestClient(app)


@pytest.fixture

def clear_mock_db():

    mock_db.clear()



def test_create_user():

    response = client.post("/register/", json={

        "username": "testuser",

        "email": "Hacklift@gmail.com",

        "password": "testpassword"

    })

    assert response.status_code == 200

    assert response.json() == {"username": "testuser", "email": "Hacklift@gmail.com", "password": "testpassword"}


def test_register_existing_username(clear_mock_db):

    """Test registration with an existing username."""


    client.post("/register/", json={

        "username": "testuser",

        "email": "test1@example.com",

        "password": "testpassword1"

    })


    response = client.post("/register/", json={

        "username": "testuser",

        "email": "test2@example.com",

        "password": "testpassword2"

    })

    assert response.status_code == 400

    assert response.json() == {"detail": "Username already taken"}




def test_register_existing_email(clear_mock_db):



    client.post("/register/", json={

        "username": "user1",

        "email": "test@example.com",

        "password": "testpassword1"

    })


    response = client.post("/register/", json={

        "username": "user2",

        "email": "test@example.com",

        "password": "testpassword2"

    })

    assert response.status_code == 400

    assert response.json() == {"detail": "Email already registered"}



def test_list_users(clear_mock_db):

    response = client.get("/users/")

    assert response.status_code == 200

    assert response.json() == []





def test_list_users_with_users(clear_mock_db):


    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))

    mock_db.append(User(username="user2", email="test2@example.com", password="password2"))


    response = client.get("/users/")

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 2

    assert response_data[0]["username"] == "user1"

    assert response_data[0]["email"] == "test1@example.com"

    assert response_data[1]["username"] == "user2"

    assert response_data[1]["email"] == "test2@example.com"



def test_login_with_username():

    """Test successful login using the username."""



    test_user = User(username="user1", email="test1@example.com", password="password1")

    mock_db.append(test_user)



    response = client.post("/login/", json={"username_or_email":"user1", "password":"password1"})

    print(response.text)



    assert response.status_code == 200

    assert response.json()["message"] == "Login successful"

    assert response.json()["user"]["username"] == test_user.username

    assert response.json()["user"]["email"] == test_user.email


def test_login_with_email():

    """Test successful login using the email."""


    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))



    response = client.post("/login/", json={"username_or_email": "test1@example.com", "password": "password1"})

    assert response.status_code == 200

    assert response.json()["message"] == "Login successful"

    assert response.json()["user"]["username"] == "user1"

    assert response.json()["user"]["email"] == "test1@example.com"


def test_login_invalid_username_or_email():

    """Test login failure with invalid username or email."""


    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))



    response = client.post("/login/", json={"username_or_email": "invaliduser", "password": "password1"})

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid credentials"



    response = client.post("/login/", json={"username_or_email": "invalidemail@example.com", "password": "password1"})

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid credentials"


def test_login_invalid_password():

    """Test login failure with an invalid password."""


    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))



    response = client.post("/login/", json={"username_or_email": "user1", "password": "wrongpassword"})

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid credentials"

