import os

from ....app.db.core.connection import get_user_tokens_collection, fernet


async def save_user_token(user_id: str, token: str):

    encrypted = fernet.encrypt(token.encode()).decode()

    collection = get_user_tokens_collection()


    await collection.update_one(

        {"user_id": user_id},

        {"$set": {"token": encrypted}},

        upsert=True

    )


async def get_user_token(user_id: str):

    collection = get_user_tokens_collection()

    record = await collection.find_one({"user_id": user_id})


    if record and "token" in record:

        return fernet.decrypt(record["token"].encode()).decode()


    return None


