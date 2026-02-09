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

# Tests for the user registration functionality
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
    # Register the first user
    client.post("/register/", json={
        "username": "testuser",
        "email": "test1@example.com",
        "password": "testpassword1"
    })
    # Attempt to register another user with the same username
    response = client.post("/register/", json={
        "username": "testuser",
        "email": "test2@example.com",
        "password": "testpassword2"
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already taken"}


# Test registration with an existing email.
def test_register_existing_email(clear_mock_db):
    
    # Register the first user
    client.post("/register/", json={
        "username": "user1",
        "email": "test@example.com",
        "password": "testpassword1"
    })
    # Attempt to register another user with the same email
    response = client.post("/register/", json={
        "username": "user2",
        "email": "test@example.com", 
        "password": "testpassword2"
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

# test the list of users
def test_list_users(clear_mock_db):
    response = client.get("/users/")
    assert response.status_code == 200
    assert response.json() == []


    
# Test listing users when users are present.
def test_list_users_with_users(clear_mock_db):
    # Add a user to the mock database
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
    
    # Add a user to the mock database
    test_user = User(username="user1", email="test1@example.com", password="password1")
    mock_db.append(test_user)

    # Test login with username
    response = client.post("/login/", json={"username_or_email":"user1", "password":"password1"})
    print(response.text)
    
    # Assertions to validate the response
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert response.json()["user"]["username"] == test_user.username
    assert response.json()["user"]["email"] == test_user.email

def test_login_with_email():
    """Test successful login using the email."""
    # Add a user to the mock database
    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))

    # Test login with email
    response = client.post("/login/", json={"username_or_email": "test1@example.com", "password": "password1"})
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert response.json()["user"]["username"] == "user1"
    assert response.json()["user"]["email"] == "test1@example.com"

def test_login_invalid_username_or_email():
    """Test login failure with invalid username or email."""
    # Add a user to the mock database
    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))

    # Test login with an invalid username
    response = client.post("/login/", json={"username_or_email": "invaliduser", "password": "password1"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    # Test login with an invalid email
    response = client.post("/login/", json={"username_or_email": "invalidemail@example.com", "password": "password1"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_invalid_password():
    """Test login failure with an invalid password."""
    # Add a user to the mock database
    mock_db.append(User(username="user1", email="test1@example.com", password="password1"))

    # Test login with an invalid password
    response = client.post("/login/", json={"username_or_email": "user1", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
