from email.mime.text import MIMEText
import os
from typing import Any


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").rstrip("/")


def validate_header_value(name: str, value: Any) -> str:
    """Reject CR/LF so untrusted content cannot create additional headers."""
    text = str(value)
    if "\r" in text or "\n" in text:
        raise ValueError(f"{name} must not contain carriage returns or newlines")
    return text


def _message(subject: Any, body: str, to: str, sender_email: str) -> MIMEText:
    msg = MIMEText(body)
    msg["Subject"] = validate_header_value("Subject", subject)
    msg["From"] = validate_header_value("From", sender_email)
    msg["To"] = validate_header_value("To", to)
    return msg


def render_email(
    template_id: str,
    to: str,
    vars: dict,
    *,
    sender_email: str,
) -> MIMEText:
    """Render a provider-specific email with validated transport headers."""
    if template_id == "quiz_link":
        subject = f"Check out this quiz: {vars['title']}"
        body = (
            "Here's a quiz we thought you'd like:\n\n"
            f"Title: {vars['title']}\n"
            f"Description: {vars['description']}\n"
            f"Access it here: {vars['link']}\n\nEnjoy!"
        )
        return _message(subject, body, to, sender_email)

    if template_id == "live_quiz_invite":
        title = vars.get("title", "Live Quiz")
        link = vars.get("link", "")
        message = vars.get("message", "").strip()
        time_limit_minutes = vars.get("time_limit_minutes", "")
        access_code_expires_at = vars.get("access_code_expires_at", "")
        subject = f"You're invited to take a live quiz: {title}"
        details = []
        if time_limit_minutes:
            details.append(f"Quiz duration: {time_limit_minutes} minutes")
        if access_code_expires_at:
            details.append(f"Access expires: {access_code_expires_at}")
        details_text = "\n".join(details)
        body = f"""You've been invited to take a live quiz on Quiz Generator.

Quiz: {title}
{message + chr(10) if message else ""}
Open the live quiz link:
{link}

{details_text}
"""
        return _message(subject, body, to, sender_email)

    if template_id == "verification":
        code = vars.get("code", "")
        token = vars.get("token", "")
        subject = "Please verify your account on Quiz Generator"
        body = f"""Thank you for registering!

To verify your email, you can either:
1. Enter the OTP: {code}
2. Or click the following link: {ALLOWED_ORIGINS}/auth/verify-email/?token={token}
"""
    elif template_id == "password_reset":
        code = vars.get("code", "")
        token = vars.get("token", "")
        subject = "Reset your password on Quiz Generator"
        body = f"""You requested to reset your password.

You can either:
1. Enter this OTP: {code}
2. Or click this link: {ALLOWED_ORIGINS}/auth/reset-password/?token={token}

If you didn't request this, just ignore this message.
"""
    else:
        subject = vars.get("subject", "Notification")
        body = vars.get("body", "")

    return _message(subject, body, to, sender_email)
