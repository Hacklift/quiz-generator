from server.celery_config import celery
from server.email_utils import send_otp_email

@celery.task
def send_otp_task(email: str, otp: str, token: str, mode="register"):
    try:
        return send_otp_email(email, otp, token, mode=mode)
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False

@celery.task
def send_password_reset_email(email: str, otp: str, token: str):
    try:
        return send_otp_email(email, otp, token, mode="reset") 
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False