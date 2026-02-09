import os
from dotenv import load_dotenv

load_dotenv()

PRIMARY_EMAIL_PROVIDER = os.getenv("PRIMARY_EMAIL_PROVIDER", "smtp").lower()

def chain_for(purpose: str, priority: str = "default") -> list[str]:
    """
    Decide email sending chain dynamically based on PRIMARY_EMAIL_PROVIDER
    and purpose.

    Rules:
    - If Mailgun is the primary provider, use it first, then SMTP-based fallbacks.
    - If SMTP is the primary provider, use Celery → Background → Direct first,
      then fall back to Mailgun.
    """
    if PRIMARY_EMAIL_PROVIDER == "mailgun":
        if purpose in ("verification", "password_reset"):
            return ["mailgun", "celery", "background", "direct"]
        return ["mailgun", "celery", "background"]
    
    if purpose in ("verification", "password_reset"):
        return ["celery", "background", "direct", "mailgun"]
    return ["celery", "background", "mailgun"]
