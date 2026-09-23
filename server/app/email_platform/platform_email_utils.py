import logging

import smtplib

import ssl

import time

import socket

from email.mime.text import MIMEText

from dotenv import load_dotenv

from .config import require_smtp_config
from .renderer import validate_header_value


load_dotenv()


logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)



smtp_config = require_smtp_config()
sender_email = smtp_config.sender_email
sender_password = smtp_config.sender_password
email_host = smtp_config.host
email_port = smtp_config.port



MAX_RETRIES = 5

RETRY_DELAY = 3

SMTP_TIMEOUT = 20



def compose_quiz_email(recipient: str, title: str, description: str, shareable_link: str) -> MIMEText:

    subject = f"Check out this quiz: {title}"

    body = (

        f"Here's a quiz we thought you'd like:\n\n"

        f"Title: {title}\n"

        f"Description: {description}\n"

        f"Access it here: {shareable_link}\n\nEnjoy!"

    )

    message = MIMEText(body)

    message["Subject"] = validate_header_value("Subject", subject)
    message["From"] = validate_header_value("From", sender_email)
    message["To"] = validate_header_value("To", recipient)

    return message



def _send_one(recipient: str, message: MIMEText) -> None:

    """
    Send using SMTP on port 587 with STARTTLS.
    Includes EHLO before and after STARTTLS and a proper SSL context.
    """

    context = ssl.create_default_context()

    with smtplib.SMTP(email_host, email_port, timeout=SMTP_TIMEOUT) as server:

        server.ehlo()

        server.starttls(context=context)

        server.ehlo()

        server.login(sender_email, sender_password)

        server.sendmail(sender_email, recipient, message.as_string())



def send_email(recipient: str, message: MIMEText) -> None:

    attempt = 0

    while attempt < MAX_RETRIES:

        try:

            _send_one(recipient, message)

            logger.info(f"[Email] Email successfully sent to {recipient}")

            return

        except (

            smtplib.SMTPServerDisconnected,

            smtplib.SMTPConnectError,

            smtplib.SMTPHeloError,

            smtplib.SMTPAuthenticationError,

            smtplib.SMTPException,

            socket.timeout,

            ssl.SSLError,

            ConnectionRefusedError,

        ) as e:

            attempt += 1

            logger.warning(f"[Email Retry] Attempt {attempt}/{MAX_RETRIES} failed for {recipient}: {e}")

            if attempt < MAX_RETRIES:

                delay = RETRY_DELAY * attempt

                logger.info(f"[Email Retry] Retrying in {delay} seconds...")

                time.sleep(delay)

            else:

                logger.error(

                    f"[Email Error] All {MAX_RETRIES} attempts failed for {recipient}.",

                    exc_info=True

                )

                raise
