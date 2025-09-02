# Email Platform Service

Reusable email service with fallbacks:

1. **Celery** (enqueue task) → 2) **BackgroundTasks** (in-process) → 3) **Direct** (sync SMTP)

## How to use (FastAPI)

```python
from fastapi import Depends
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService

@router.post("/send-verification")
async def send_verification(email_svc: EmailService = Depends(get_email_service)):
    await email_svc.send_email(
        to="user@example.com",
        template_id="verification",           # "quiz_link" | "verification" | "password_reset"
        template_vars={"code": "123456"},     # per template below
        purpose="verification",               # selects fallback chain
        priority="default",
    )
    return {"message": "ok"}
```

## Purposes → Chains

- `quiz_link` → Celery → Background
- `verification`, `password_reset` → Celery → Background → Direct

## Templates (vars)

- `quiz_link`: `title`, `description`, `link`
- `verification`: `code`
- `password_reset`: `reset_link`
- other: pass `subject`, `body`

## Env / Worker

- SMTP: `SENDER_EMAIL`, `SENDER_PASSWORD`, `EMAIL_HOST`, `EMAIL_PORT`
- Celery worker:
  `celery -A server.celery_config.celery_app worker -Q email,celery --loglevel=info --pool=solo`
