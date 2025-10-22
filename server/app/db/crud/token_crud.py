import os
from cryptography.fernet import Fernet
from ....app.db.core.connection import get_user_tokens_collection, fernet

# Load Fernet key from environment
FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY)

async def save_user_token(user_id: str, token: str):
    """Encrypt and save user's AI token."""
    encrypted_token = fernet.encrypt(token.encode()).decode()
    collection = get_user_tokens_collection()
    await collection.update_one(
        {"user_id": user_id},
        {"$set": {"token": encrypted_token}},
        upsert=True
    )

async def get_user_token(user_id: str):
    """Fetch and decrypt user's AI token if it exists."""
    collection = get_user_tokens_collection()
    record = await collection.find_one({"user_id": user_id})
    if record and "token" in record:
        return fernet.decrypt(record["token"].encode()).decode()
    return None
