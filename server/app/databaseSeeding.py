import asyncio
from motor.motor_asyncio import AsyncIOMotorCollection
from .db.core.connection import quizzes_collection, users_collection
from .seed_data import seed_quizzes, seed_user_data
from datetime import datetime, timezone
from .core.security import hash_password
from .quiz.schemas.quiz_schemas import NewQuizSchema as SeedQuiz
from .quiz.seed_data.seed_all_categories import seed_all
from .users.identity import (
    USER_SCHEMA_VERSION,
    build_profile,
    default_user_status,
    normalize_email,
    normalize_username,
)
from .users.models import SeedUser
from typing import List


async def is_collection_empty(collection: AsyncIOMotorCollection) -> bool:
    count = await collection.count_documents({})
    return count == 0


async def seed_quizzes_collection(collection: AsyncIOMotorCollection, seed_data: List[dict]):
    if await is_collection_empty(collection):
        for data in seed_data:
            quiz_data = data.copy()
            try:
                quiz = SeedQuiz(**quiz_data)
                await collection.insert_one(quiz.model_dump())
                print(f"Quiz '{quiz.title}' inserted successfully.")
            except Exception as e:
                print(f"Error inserting quiz: {e}")
    else:
        print("Quizzes collection already has data. Skipping seeding.")


async def seed_users_collection(collection: AsyncIOMotorCollection, seed_data: List[dict]):
    if await is_collection_empty(collection):
        for data in seed_data:
            user_data = data.copy()
            try:
                user_data["hashed_password"] = hash_password(user_data.pop("password"))
                user_data["is_active"] = True
                user_data["is_verified"] = user_data.get("is_verified", False)
                user_data["status"] = default_user_status(user_data["is_verified"])
                user_data["role"] = "user"
                user_data["email_normalized"] = normalize_email(user_data["email"])
                user_data["username_normalized"] = normalize_username(user_data["username"])
                user_data["profile"] = build_profile(full_name=user_data.pop("full_name", None))
                user_data["schema_version"] = USER_SCHEMA_VERSION
                user_data["created_at"] = datetime.now(timezone.utc)
                user_data["updated_at"] = datetime.now(timezone.utc)
                user = SeedUser(**user_data)
                await collection.insert_one(user.model_dump())
                print(f"User '{user.email}' inserted successfully.")
            except Exception as e:
                print(f"Error inserting user: {e}")
    else:
        print("Users collection already has data. Skipping seeding.")


async def restoreSeed_quizzes_collection(collection: AsyncIOMotorCollection, seed_data: List[dict]):
    await collection.delete_many({})
    for data in seed_data:
        quiz_data = data.copy()
        try:
            quiz = SeedQuiz(**quiz_data)
            await collection.insert_one(quiz.model_dump())
            print(f"Quiz '{quiz.title}' inserted successfully.")
        except Exception as e:
            print(f"Error inserting quiz: {e}")


async def restoreSeed_users_collection(collection: AsyncIOMotorCollection, seed_data: List[dict]):
    await collection.delete_many({})
    for data in seed_data:
        user_data = data.copy()
        try:
            user_data["hashed_password"] = hash_password(user_data.pop("password"))  
            user_data["is_active"] = True
            user_data["is_verified"] = user_data.get("is_verified", False)
            user_data["status"] = default_user_status(user_data["is_verified"])
            user_data["role"] = "user"
            user_data["email_normalized"] = normalize_email(user_data["email"])
            user_data["username_normalized"] = normalize_username(user_data["username"])
            user_data["profile"] = build_profile(full_name=user_data.pop("full_name", None))
            user_data["schema_version"] = USER_SCHEMA_VERSION
            user_data["created_at"] = datetime.now(timezone.utc)
            user_data["updated_at"] = datetime.now(timezone.utc)
            user = SeedUser(**user_data)
            await collection.insert_one(user.model_dump())
            print(f"User '{user.email}' inserted successfully.")
        except Exception as e:
            print(f"Error inserting user: {e}")


async def restoreSeed_category_quizzes():
    try:
        await seed_all()
        print("V2 category quizzes restored successfully.")
    except Exception as e:
        print(f"Error restoring V2 category quizzes: {e}")


async def seed_database():
    await asyncio.gather(
        seed_quizzes_collection(quizzes_collection, seed_quizzes),
        seed_users_collection(users_collection, seed_user_data),
        seed_all()
    )
    print("Database seeding process completed!")


async def restoreSeed_database():
    await asyncio.gather(
        restoreSeed_quizzes_collection(quizzes_collection, seed_quizzes),
        restoreSeed_users_collection(users_collection, seed_user_data),
        restoreSeed_category_quizzes()
    )
    print("Database Restore and Seeding completed!")
