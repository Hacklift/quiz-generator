from email.mime.text import MIMEText
import os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").rstrip("/")
SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL", os.getenv("MAILGUN_SENDER_EMAIL", "no-reply@example.com")
)

def render_email(template_id: str, to: str, vars: dict) -> MIMEText:
    """
    Returns a MIMEText with Subject/From/To set.
    Supported template vars:
      - quiz_link:      title, description, link
      - live_quiz_invite: title, link, message, time_limit_minutes, access_code_expires_at
      - verification:   code, token  (renderer builds verify_link)
      - password_reset: code, token  (renderer builds reset_link)
      - custom:         subject, body
    """
    if template_id == "quiz_link":
        subject = f"Check out this quiz: {vars['title']}"
        body = (
            f"Here's a quiz we thought you'd like:\n\n"
            f"Title: {vars['title']}\n"
            f"Description: {vars['description']}\n"
            f"Access it here: {vars['link']}\n\nEnjoy!"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to
        return msg

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
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to
        return msg

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
    msg["From"] = SENDER_EMAIL
    msg["To"] = to
    return msg
