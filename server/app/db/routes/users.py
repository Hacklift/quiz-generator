from fastapi import APIRouter, HTTPException, Depends

from motor.motor_asyncio import AsyncIOMotorCollection

from ....app.db.crud.user_crud import (

    create_user,

    get_user_by_id,

    get_user_by_email,

    update_user,

    delete_user,

    list_users

)

from ....app.db.core.connection import get_users_collection

from ..schemas.user_schemas import (

    CreateUserRequest,

    NewUserSchema,

    UserSchema,

    DeleteUserResponse,

    UpdateUserSchema

)

from server.schemas.model import LoginRequestModel


from ..utils import is_valid_password


router = APIRouter()


@router.post("/test/create-user", response_model=NewUserSchema)

async def register_user(

    user: CreateUserRequest,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    created_user = await create_user(users_collection, user)

    if not created_user:

        raise HTTPException(status_code=500, detail="Failed to create user")

    return created_user


@router.get("/test/get-user/{user_id}", response_model=UserSchema)

async def get_user(

    user_id: str,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    user = await get_user_by_id(users_collection, user_id)

    if not user:

        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/test/get-user-by-email/{email}", response_model=UserSchema)

async def get_user_by_email_endpoint(

    email: str,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    user = await get_user_by_email(users_collection, email)

    if not user:

        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/test/list-users", response_model=list[UserSchema])

async def get_all_users(users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):

    return await list_users(users_collection)


@router.put("/test/update-user/{user_id}", response_model=UserSchema)

async def update_existing_user(

    user_id: str, user_update: UpdateUserSchema,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    updated_user = await update_user(users_collection, user_id, user_update)

    if not updated_user:

        raise HTTPException(status_code=404, detail="User not found")

    return updated_user


@router.delete("/test/delete-user/{user_id}", response_model=DeleteUserResponse)

async def delete_existing_user(

    user_id: str,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    result = await delete_user(users_collection, user_id)

    if result.delete_count == 0:

        raise HTTPException(status_code=404, detail="User not found")

    return result


@router.post("/test/login/")

async def login_user(

    request: LoginRequestModel,

    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)

):

    identifier = request.username_or_email
    if not identifier:
        raise HTTPException(status_code=400, detail="Username or email is required")

    user = await users_collection.find_one(

        {"$or": [{"username": identifier}, {"email": identifier}]}

    )


    if not user or not is_valid_password(request.password, user["hashed_password"]):

        raise HTTPException(status_code=401, detail="Invalid credentials")


    return {
        "message": "Login successful",
        "user_id": str(user["_id"]),
        "username": user["username"],
        "fullname": user.get("full_name", ""),
        "email": user["email"],
        "role": user.get("role", "user"),
    }
