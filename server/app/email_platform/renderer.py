from email.mime.text import MIMEText
from server.app.share.share_email_utils import compose_quiz_email, sender_email

def render_email(template_id: str, to: str, vars: dict) -> MIMEText:
    """
    Returns a ready-to-send MIMEText message with Subject/From/To set.
    """
    if template_id == "quiz_link":
        # expects: title, description, link
        return compose_quiz_email(to, vars["title"], vars["description"], vars["link"])

    if template_id == "verification":
        subject = "Verify your email"
        body = f"Your verification code is: {vars.get('code','')}\nThis code expires in 10 minutes."
    elif template_id == "password_reset":
        subject = "Reset your password"
        body = f"Use this link to reset your password: {vars.get('reset_link','')}\nIf you didn’t request this, ignore this email."
    else:
        subject = vars.get("subject", "Notification")
        body = vars.get("body", "")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to
    return msg
