from pydantic import BaseModel, EmailStr





class ShareQuizResponse(BaseModel):

    link: str



class ShareEmailRequest(BaseModel):

    quiz_id: str

    recipient_email: EmailStr

    shareableLink: str



class ShareEmailResponse(BaseModel):

    message: str


