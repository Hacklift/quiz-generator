from pydantic import BaseModel


class LoginRequestModel(BaseModel):

    username_or_email: str

    password: str

