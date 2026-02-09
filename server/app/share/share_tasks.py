import logging

import ssl

import smtplib

import socket

from email.mime.text import MIMEText


from server.celery_config import celery_app

from .share_email_utils import send_email, sender_email


logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)



@celery_app.task(

    name="tasks.send_email_generic",

    bind=True,

    autoretry_for=(ssl.SSLError, smtplib.SMTPException, socket.timeout, ConnectionError, TimeoutError),

    retry_backoff=5,

    retry_jitter=True,

    retry_kwargs={"max_retries": 3},

)

def send_email_generic(self, recipient: str, subject: str, body: str):

    """
    Generic email task used by the platform email service for ANY template/purpose.
    Relies on share_email_utils.send_email() which already has its own retry loop.
    This task adds job-level retries to handle transient provider/network issues.
    """

    try:

        msg = MIMEText(body)

        msg["Subject"] = subject

        msg["From"] = sender_email

        msg["To"] = recipient


        send_email(recipient, msg)

        logger.info(f"[Celery Task] Completed send_email_generic for {recipient}")

    except Exception as e:

        logger.error(f"[Celery Task Error] Failure in send_email_generic: {e}", exc_info=True)

        raise


