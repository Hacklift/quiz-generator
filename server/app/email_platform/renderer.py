from email.mime.text import MIMEText
import os
from server.app.email_platform.platform_email_utils import compose_quiz_email, sender_email

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").rstrip("/")

def render_email(template_id: str, to: str, vars: dict) -> MIMEText:
    """
    Returns a MIMEText with Subject/From/To set.
    Supported template vars:
      - quiz_link:      title, description, link
      - verification:   code, token  (renderer builds verify_link)
      - password_reset: code, token  (renderer builds reset_link)
      - custom:         subject, body
    """
    if template_id == "quiz_link":
        return compose_quiz_email(to, vars["title"], vars["description"], vars["link"])

    if template_id == "verification":
        code  = vars.get("code", "")
        token = vars.get("token", "")
        verify_link = f"{ALLOWED_ORIGINS}/auth/verify-email/?token={token}"
        subject = "Please verify your account on Quiz Generator"
        body = f"""Thank you for registering!

To verify your email, you can either:
1. Enter the OTP: {code}
2. Or click the following link: {verify_link}
"""
    elif template_id == "password_reset":
        code  = vars.get("code", "")
        token = vars.get("token", "")
        reset_link = f"{ALLOWED_ORIGINS}/auth/reset-password/?token={token}"
        subject = "Reset your password on Quiz Generator"
        body = f"""You requested to reset your password.

You can either:
1. Enter this OTP: {code}
2. Or click this link: {reset_link}

If you didn't request this, just ignore this message.
"""
    else:
        subject = vars.get("subject", "Notification")
        body = vars.get("body", "")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to
    return msg
