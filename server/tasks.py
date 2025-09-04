from server.celery_config import celery
from server.email_utils import send_otp_email
import logging

logger = logging.getLogger(__name__)

@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={'max_retries': 3})
def send_otp_task(self, email: str, otp: str, token: str, mode="register"):
    try:
        return send_otp_email(email, otp, token, mode=mode)
    except Exception as e:
        logger.error(f"Error sending OTP email to {email}: {e}")
        raise self.retry(exc=e)

@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={'max_retries': 3})
def send_password_reset_email(self, email: str, otp: str, token: str):
    try:
        return send_otp_email(email, otp, token, mode="reset")
    except Exception as e:
        logger.error(f"Error sending password reset email to {email}: {e}")
        raise self.retry(exc=e)