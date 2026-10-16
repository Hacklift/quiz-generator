# Email Platform Service

Reusable, centralized email service with provider-specific **fallbacks**:

1. **Celery** (enqueue task) → 2. **BackgroundTasks** (in-process) → 3. **Direct** (sync SMTP)

## Usage (FastAPI)

```python
from fastapi import Depends
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService

@router.post("/send-verification")
async def send_verification(email_svc: EmailService = Depends(get_email_service)):
    await email_svc.send_email(
        to="user@example.com",
        template_id="verification",           # "quiz_link" | "verification" | "password_reset"
        template_vars={"code": "123456", "token": "abc123"},
        purpose="verification",               # selects fallback chain
        priority="default",
    )
    return {"message": "ok"}
```

## Purpose → Fallback Chains

- `quiz_link` → Celery → Background
- `verification` → Celery → Background → Direct
- `password_reset` → Celery → Background → Direct

## Templates

- **quiz_link**: `title`, `description`, `link`
- **verification**: `code`, `token` (link auto-built as `/verify-link/?token=...`)
- **password_reset**: `code`, `token` (link auto-built as `/reset-password-link/?token=...`)
- **custom/other**: supply `subject`, `body` directly

## Environment

- SMTP delivery requires `SENDER_EMAIL`, `SENDER_PASSWORD`, `EMAIL_HOST`, and
  `EMAIL_PORT` (587 + STARTTLS expected).
- Mailgun delivery requires `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, and
  `MAILGUN_SENDER_EMAIL`. The configured Mailgun sender must belong to the
  verified Mailgun domain (or one of its subdomains).
- `BACKEND_URL` (used to build verification/reset links)
- `REDIS_URL` (for Celery broker/backend)

Email rendering does not resolve configuration itself. Each adapter supplies
its own validated sender identity, so Mailgun can operate without SMTP
credentials while SMTP remains a fail-fast fallback when it is selected.

## Worker

Start worker with email queue:

```bash
celery -A server.celery_config.celery_app worker \
  -Q email,celery --loglevel=info --pool=solo
```

### How to call outside FastAPI

You can import and build the service directly:

```python
from server.app.email_platform.service import build_email_service

# Build without BackgroundTasks (Celery + Direct only)
email_svc = build_email_service()

# Use it
await email_svc.send_email(
    to="user@example.com",
    template_id="verification",
    template_vars={"code": "123456", "token": "abc123"},
    purpose="verification",
    priority="default",
)
```

### Key difference

- **Inside FastAPI**: `BackgroundTasks` fallback is available.
- **Outside FastAPI**: You’ll get Celery → Direct, but skip Background unless you manually construct a `BackgroundTasks` and pass it in.
