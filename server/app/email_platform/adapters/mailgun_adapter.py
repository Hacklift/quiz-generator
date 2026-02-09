import os
import logging
import requests
from email.mime.text import MIMEText
from ..models import EmailPayload, SendResult
from ..renderer import render_email

logger = logging.getLogger(__name__)

MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
MAILGUN_SENDER_EMAIL = os.getenv(
    "MAILGUN_SENDER_EMAIL",
    f"no-reply@{MAILGUN_DOMAIN}" if MAILGUN_DOMAIN else "no-reply@example.com"
)
MAILGUN_API_BASE_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}" if MAILGUN_DOMAIN else None


class MailgunAdapter:
    """
    Adapter for sending emails via Mailgun HTTP API.
    Uses a persistent session to ensure immediate delivery.
    """

    def __init__(self):
        if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
            logger.warning("[MailgunAdapter] Missing MAILGUN_API_KEY or MAILGUN_DOMAIN — adapter will be skipped if used.")
        
        self.session = requests.Session()
        self.session.auth = ("api", MAILGUN_API_KEY)
        self.session.headers.update({"User-Agent": "QuizAppVault-Mailer"})
        self.base_url = MAILGUN_API_BASE_URL

        try:
            self.session.get("https://api.mailgun.net/v3/domains", timeout=5)
        except Exception as e:
            logger.warning(f"[MailgunAdapter] Mailgun session warmed up error: {e}")

    async def send(self, payload: EmailPayload) -> SendResult:
        if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
            logger.error("[MailgunAdapter] Cannot send — missing configuration.")
            raise RuntimeError("Mailgun not configured")

        msg: MIMEText = render_email(payload.template_id, payload.to, payload.template_vars)
        subject = msg["Subject"]
        body = msg.get_payload()

        data = {
            "from": f"QuizAppVault <{MAILGUN_SENDER_EMAIL}>",
            "to": [payload.to],
            "subject": subject,
            "text": body,
        }

        try:
            logger.info(f"[MailgunAdapter] Sending email to {payload.to} via Mailgun...")
            response = self.session.post(f"{self.base_url}/messages", data=data)

            if response.status_code == 200:
                logger.info(f"[MailgunAdapter] Mailgun sent email to {payload.to}.")
                return SendResult(ok=True, adapter="mailgun")

            else:
                logger.error(f"[MailgunAdapter] Mailgun send failed ({response.status_code}): {response.text}")
                raise RuntimeError(f"Mailgun API error: {response.text}")

        except requests.RequestException as e:
            logger.error(f"[MailgunAdapter] Network error: {e}", exc_info=True)
            raise
