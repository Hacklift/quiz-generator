# MongoDB Database Integration

This documentation provides a detailed explanation of the MongoDB database integration for the Quiz Generator project. It includes instructions on setup, connection, and working with the database in both development and production environments.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Connection Setup](#connection-setup)
4. [Database Structure](#database-structure)
5. [CRUD Operations](#crud-operations)
6. [Seeding Data](#seeding-data)
7. [Accessing Seeded Quiz Data](#accessing-seeded-quiz-data)
8. [Best Practices](#best-practices)

---

## Introduction

MongoDB is the primary database used in this project. It stores quiz data and user-related information, allowing for efficient retrieval and management.

This guide outlines the integration process, including connection setup, CRUD functionalities, and seeding data for consistent development environments.

---

## Prerequisites

Ensure the following are installed on your development environment:

- MongoDB (local)
- Python 3.12
- Required Python packages installed from `Pipfile` and `Pipfile.lock`
- Access to the `seed_data.py` and `seed.py` files located in the `app` folder

---

## Connection Setup

The database connection is managed through the `connection.py` file located in the `db/core/` directory. This file establishes the connection to the MongoDB instance and provides access to the necessary collections. Database Indexing is also implemented in this file.

### Example of `connection.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URI)

database = client["quiz_db"]

quizzes_collection = database["quizzes"]
users_collection = database["users"]
```

---

## Database Structure

The database consists of the following collections:

- **Quizzes**: Stores quiz data including questions, options, and answers.
- **Users**: Stores user information like usernames and hashed passwords.

### Quiz Collection Example

```json
{
  "_id": "ObjectId",
  "title": "Sample Quiz",
  "description": "A sample quiz for testing purposes",
  "quiz_type": "multiple-choice",
  "questions": [
    {
      "question": "What is the capital of France?",
      "options": ["Paris", "Berlin", "Madrid", "Rome"],
      "answer": "Paris"
    }
  ]
}
```

### User Collection Example

```json
{
  "_id": "ObjectId",
  "username": "username",
  "email": "email@example.com",
  "full_name": "full_name",
  "quizzes": [],
  "is_active": true,
  "role": "user",
  "created_at": "datatime",
  "updated_at": "datetime",
  "hashed_password": "hashedpassword"
}
```

---

## CRUD Operations

CRUD operations are implemented in the `crud` folder and are structured into separate files for modularity. For example, `quiz_crud.py` handles operations related to quizzes.

### Example: create Quiz

```python
async def create_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_data: dict):
    try:
        new_quiz = await quizzes_collection.insert_one(quiz_data)
        print("new quiz successfully created with id: ", str(new_quiz.inserted_id))
        return str(new_quiz.inserted_id)
    except Exception as e:
        print(f"Error occurred while creating quiz: {e}")
        return None
```

---

## Database Models and Schemas

- **Quiz_models and Quiz_schemas**: These are the pydantic models and schemas used for validation and serialization of quiz related data accross the application.

- **User_models and User_schemas**: These are the pydantic models and schemas used for validation and serialization of user related data accross the application.

---

## Seeding Data

The project uses `seed_data.py` and `seed.py` to seed the database with default quizzes and user data.

### File Locations

- `seed_data.py`: Contains the list of quiz data and user data to be seeded.
- `seed.py`: Contains the script to populate the database with seed data.

### Seeding Instructions

1. Ensure MongoDB is running locally.
   ```bash
   sudo systemctl status mongod
   ```
2. Run the `seed.py` script from the `app` folder:
   ```bash
   PYTHONPATH=path-to-file python seed.py
   ```
   replace `path-to-file` with your actual path to the seed.py file.
3. The script clears existing quiz data and inserts seed quizzes.

---

## Accessing Seeded Quiz Data

Once the database is seeded, you can access the quiz data or user data to verify its structure and content. Below are the instructions for retrieving quiz data using both MongoDB Shell and MongoDB Compass.

### Using MongoDB Shell

1. Start the MongoDB shell:
   ```bash
   mongosh
   ```
2. Switch to the `quiz_db` database:
   ```mongoshell
   use quiz_db
   ```
3. Query the `quizzes` collection to retrieve all quiz data:
   ```mongoshell
   db.quizzes.find({}).pretty()
   ```
   This will display the complete quiz data in a readable JSON-like format.

### Using MongoDB Compass

1. Open MongoDB Compass and connect to your MongoDB instance.
2. Navigate to the `quiz_db` database and open the `quizzes` collection.
3. Use the query panel to run the following query:
   ```json
   {}
   ```
   This will display all quiz data stored in the `quizzes` collection.

### Example Output

Here’s an example of how the seeded quiz data will appear:

```json
[
  {
    "_id": "64c8e9f3f1a2bc1d2f8d2e3a",
    "title": "General Knowledge Quiz",
    "description": "A quiz to test your general knowledge.",
    "quiz_type": "multiple-choice",
    "questions": [
      {
        "question": "What is the capital of France?",
        "options": ["Paris", "Berlin", "Madrid", "Rome"],
        "answer": "Paris"
      },
      {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Earth", "Venus", "Mars", "Jupiter"],
        "answer": "Mars"
      }
    ]
  },
  {
    "_id": "64c8e9f3f1a2bc1d2f8d2e3b",
    "title": "Science Quiz",
    "description": "A quiz to test your knowledge of science.",
    "quiz_type": "multiple-choice",
    "questions": [
      {
        "question": "What is the chemical symbol for water?",
        "options": ["H2O", "CO2", "O2", "N2"],
        "answer": "H2O"
      }
    ]
  }
]
```

You can use this data for testing CRUD operations or for building new features in the project.

---

## Best Practices

1. **Environment Variables**:
   Store sensitive information, such as database URIs, in environment variables.

2. **Error Handling**:
   Implement robust error handling for database operations to ensure reliability.

3. **Idempotent Seeding**:
   Ensure the seeding process does not duplicate data.

4. **Documentation**:
   Maintain updated documentation to help team members understand the database structure and usage.

---

This document serves as a comprehensive guide to MongoDB integration in the Quiz Generator project. Update it regularly to reflect changes in the project structure or functionalities.
