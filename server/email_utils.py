import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
import logging

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler = logging.FileHandler('email_errors.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def send_otp_email(email: str, otp: str, token: str, mode="register"):
    if mode == "reset":
        subject = "Reset your password on Quiz Generator"
        verification_link = f"http://localhost:8000/reset-password-link/?token={token}"
        body = f"""
        You requested to reset your password.

        You can either:
        1. Enter this OTP: {otp}
        2. Or click this link: {verification_link}

        If you didn't request this, just ignore this message.
        """
    else:
        subject = "Please verify your account on Quiz Generator"
        verification_link = f"http://localhost:8000/verify-link/?token={token}"
        body = f"""
        Thank you for registering!

        To verify your email, you can either:
        1. Enter the OTP: {otp}
        2. Or click the following link: {verification_link}
        """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False