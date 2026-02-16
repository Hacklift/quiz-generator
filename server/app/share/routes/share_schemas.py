from pydantic import BaseModel, EmailStr
from typing import Any, Dict, List




class ShareQuizResponse(BaseModel):
    link: str


class SharedQuizDataResponse(BaseModel):
    id: str
    title: str
    description: str
    quiz_type: str
    questions: List[Dict[str, Any]]


class ShareEmailRequest(BaseModel):
    quiz_id: str
    recipient_email: EmailStr
    shareableLink: str


class ShareEmailResponse(BaseModel):
    message: str
