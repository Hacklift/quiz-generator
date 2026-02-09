from pydantic import BaseModel, EmailStr

from typing import Dict


class EmailPayload(BaseModel):

    to: EmailStr

    template_id: str

    template_vars: Dict[str, str] = {}


class SendResult(BaseModel):

    ok: bool

    adapter: str

