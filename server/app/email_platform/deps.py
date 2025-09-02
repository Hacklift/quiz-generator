from fastapi import BackgroundTasks
from .service import build_email_service, EmailService

def get_email_service(background: BackgroundTasks) -> EmailService:
    # FastAPI will inject BackgroundTasks here
    return build_email_service(background)
