from pydantic import BaseModel

from .user_model import UserModel


class LoginResponseModel(BaseModel):

    message: str

    access_token: str

    token_type: str

    user: UserModel

