from pydantic import BaseModel, EmailStr


class UserModel(BaseModel):

    username: str

    email: EmailStr

    password: str

    is_verified: bool = False


