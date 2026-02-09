from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from ..schemas.user_schemas import NewUserSchema, UpdateUserSchema, CreateUserRequest, UserSchema, DeleteUserResponse
from ..utils import hash_password
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def create_user(users_collection: AsyncIOMotorCollection, user: CreateUserRequest) -> Optional[NewUserSchema]:
    try:
        user_dict = user.model_dump()
        new_user_data = {
            **user_dict,
            "quizzes": [],
            "is_active": True,
            "is_verified": False,
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "hashed_password": hash_password(user_dict["password"])
        }
        del new_user_data["password"]

        new_user = await users_collection.insert_one(new_user_data)
        logger.info(f"New user created with ID: {new_user.inserted_id}")
    
        return  NewUserSchema(
            id=str(new_user.inserted_id),
            username=user_dict["username"],
            email=user_dict["email"],
            full_name=user_dict["full_name"],
            is_active=new_user_data["is_active"],
            is_verified=new_user_data["is_verified"],
            role=new_user_data["role"],
            created_at=new_user_data["created_at"],
            updated_at=new_user_data["updated_at"]
        ) 
    
    except PyMongoError as e:
        logger.error(f"Database error while creating user: {e}")
    except ValueError as e:
        logger.error(f"Invalid data: {e}")
    return None

async def get_user_by_id(users_collection: AsyncIOMotorCollection, user_id: str) -> Optional[UserSchema]:
    try:
        user = await users_collection.find_one(
            {"_id": ObjectId(user_id)}, projection={"hashed_password": 0}
            )
        if user:
            return UserSchema(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"],
                full_name=user["full_name"],
                quizzes=user["quizzes"],
                is_active=user["is_active"],
                is_verified=user.get("is_verified", False),
                role=user["role"],
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )
        return None
    
    except InvalidId:
        logger.error(f"Invalid user_id format: {user_id}")
    except PyMongoError as e:
        logger.error(f"Error retrieving user by ID: {e}")
    return None


async def get_user_by_email(users_collection: AsyncIOMotorCollection, email: str) -> Optional[UserSchema]:
    try:
        user = await users_collection.find_one(
            {"email": email}, projection={"hashed_password": 0}
            )
        if user:
             return UserSchema(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"],
                full_name=user["full_name"],
                quizzes=user["quizzes"],
                is_active=user["is_active"],
                is_verified=user.get("is_verified", False),
                role=user["role"],
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )
        return None
    
    except PyMongoError as e:
        logger.error(f"Error retrieving user by email: {e}")
    return None



async def update_user(users_collection: AsyncIOMotorCollection, user_id: str, user_update: UpdateUserSchema) -> Optional[UserSchema]:
    try:
        update_data = user_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        password = update_data.pop("password", None)  
        if password:
            update_data["hashed_password"] = hash_password(password)

        updated_user = await users_collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )

        if updated_user:
            logger.info(f"User {user_id} updated successfully") 
            user_dict = dict(updated_user)
            user_dict["id"] = str(updated_user["_id"])
            user_dict.pop("_id", None)
            user_dict.pop("hashed_password", None)

            return UserSchema(**user_dict)

        return None
    
    except InvalidId:
        logger.error(f"Invalid user_id format: {user_id}")
    except PyMongoError as e:
        logger.error(f"Database error while updating user: {e}")
    return None
    



async def delete_user(users_collection: AsyncIOMotorCollection, user_id: str) -> Optional[DeleteUserResponse]:
    try:
        result = await users_collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0 :
            return DeleteUserResponse(
                message=f"User with ID {user_id} deleted successfully",
                delete_count=result.deleted_count
            )
        
        return DeleteUserResponse(
            message="User not found",
            delete_count=0
        )
    
    except PyMongoError as e:
        logger.error(f"Error while deleting user: {e}")

    return DeleteUserResponse(
            message="An error occurred while deleting the user",
            delete_count=0
        )


async def list_users(users_collection: AsyncIOMotorCollection) -> List[UserSchema]:
    try:
        users_cursor = users_collection.find({}, projection={"hashed_password": 0})
        users = await users_cursor.to_list(length=None)

        return [
        UserSchema(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        quizzes=user["quizzes"],
        is_active=user["is_active"],
        is_verified=user.get("is_verified", False),
        role=user["role"],
        created_at=user["created_at"],
        updated_at=user["updated_at"]
        )
        for user in users
        ]

    except PyMongoError as e:
        logger.error(f"Database error while listing users: {e}")
    return []

