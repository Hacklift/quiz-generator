from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ....app.db.crud.token_crud import save_user_token, get_user_token

router = APIRouter()

class TokenIn(BaseModel):
    token: str

DUMMY_USER_ID = "dev_user"  # temporary user_id for development

@router.post("/user/token")
async def add_token(token_in: TokenIn):
    await save_user_token(DUMMY_USER_ID, token_in.token)
    return {"message": "Token saved successfully"}

@router.get("/user/token")
async def fetch_token():
    token = await get_user_token(DUMMY_USER_ID)
    if not token:
        raise HTTPException(status_code=404, detail="No token found for user")
    return {"token": token}
