import os
import logging
import requests
from email.mime.text import MIMEText
from ..models import EmailPayload, SendResult
from ..renderer import render_email

logger = logging.getLogger(__name__)

class MailgunAdapter:
    """
    Adapter for sending emails via Mailgun HTTP API.
    Uses a persistent session to ensure immediate delivery.
    """

    def __init__(self):
        self.api_key = os.getenv("MAILGUN_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        self.sender_email = os.getenv(
            "MAILGUN_SENDER_EMAIL",
            f"no-reply@{self.domain}" if self.domain else "no-reply@example.com"
        )
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}" if self.domain else None

        if not self.api_key or not self.domain:
            logger.warning("[MailgunAdapter] Missing MAILGUN_API_KEY or MAILGUN_DOMAIN — adapter will be skipped if used.")
        
        self.session = requests.Session()
        self.session.auth = ("api", self.api_key)
        self.session.headers.update({"User-Agent": "QuizAppVault-Mailer"})

        if os.getenv("MAILGUN_WARMUP", "1") == "1":
            try:
                self.session.get("https://api.mailgun.net/v3/domains", timeout=5)
            except Exception as e:
                logger.warning(f"[MailgunAdapter] Mailgun session warmed up error: {e}")

    async def send(self, payload: EmailPayload) -> SendResult:
        if not self.api_key or not self.domain:
            logger.error("[MailgunAdapter] Cannot send — missing configuration.")
            raise RuntimeError("Mailgun not configured")

        msg: MIMEText = render_email(payload.template_id, payload.to, payload.template_vars)
        subject = msg["Subject"]
        body = msg.get_payload()

        data = {
            "from": f"QuizAppVault <{self.sender_email}>",
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
