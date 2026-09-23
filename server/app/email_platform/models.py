from typing import Optional

from pydantic import BaseModel, EmailStr

from typing import Dict


class EmailPayload(BaseModel):

    to: EmailStr

    template_id: str

    template_vars: Dict[str, str] = {}


class SendResult(BaseModel):

    ok: bool

    adapter: str

    provider_message_id: Optional[str] = None
