import os
import logging
import requests
from email.mime.text import MIMEText
from ..models import EmailPayload, SendResult
from ..renderer import render_email
from ..config import require_mailgun_config

logger = logging.getLogger(__name__)
MAILGUN_REQUEST_TIMEOUT_SECONDS = 20

class MailgunAdapter:
    """
    Adapter for sending emails via Mailgun HTTP API.
    Uses a persistent session to ensure immediate delivery.
    """

    def __init__(self):
        self.api_key = None
        self.domain = None
        self.sender_email = None
        self.base_url = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "QuizAppVault-Mailer"})

        if os.getenv("MAILGUN_WARMUP", "0") == "1":
            try:
                self.session.get("https://api.mailgun.net/v3/domains", timeout=5)
            except Exception as e:
                logger.warning(f"[MailgunAdapter] Mailgun session warmed up error: {e}")

    async def send(self, payload: EmailPayload) -> SendResult:
        config = require_mailgun_config()
        self.api_key = config.api_key
        self.domain = config.domain
        self.sender_email = config.sender_email
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}"
        self.session.auth = ("api", self.api_key)

        msg: MIMEText = render_email(
            payload.template_id,
            payload.to,
            payload.template_vars,
            sender_email=self.sender_email,
        )
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
            response = self.session.post(
                f"{self.base_url}/messages",
                data=data,
                timeout=MAILGUN_REQUEST_TIMEOUT_SECONDS,
            )

            if 200 <= response.status_code < 300:
                logger.info(f"[MailgunAdapter] Mailgun sent email to {payload.to}.")
                try:
                    provider_message_id = response.json().get("id")
                except (AttributeError, ValueError):
                    provider_message_id = None
                return SendResult(
                    ok=True,
                    adapter="mailgun",
                    provider_message_id=provider_message_id,
                )

            else:
                logger.error(f"[MailgunAdapter] Mailgun send failed ({response.status_code}): {response.text}")
                raise RuntimeError(f"Mailgun API error: {response.text}")

        except requests.RequestException as e:
            logger.error(f"[MailgunAdapter] Network error: {e}", exc_info=True)
            raise
