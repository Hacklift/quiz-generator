from fastapi import APIRouter, Depends

from pydantic import BaseModel

from ....app.db.crud.token_crud import save_user_token, get_user_token

from ....app.dependancies import get_current_user


router = APIRouter()


class TokenIn(BaseModel):

    token: str


@router.post("/user/token")

async def add_token(token_in: TokenIn, user=Depends(get_current_user)):

    await save_user_token(user.id, token_in.token)

    return {"message": "Token saved successfully"}


@router.get("/user/token")

async def fetch_token(user=Depends(get_current_user)):

    token = await get_user_token(user.id)
    return {"token": token or None}
