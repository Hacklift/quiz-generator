"""Configuration shared by every email provider."""

from dataclasses import dataclass
import os


def require_env(var_name: str) -> str:
    """Read a required non-blank environment value without provider coupling."""
    value = os.getenv(var_name, "").strip()
    if not value:
        raise EnvironmentError(
            f"[Config Error] Required environment variable '{var_name}' is missing."
        )
    return value


@dataclass(frozen=True)
class SmtpConfig:
    sender_email: str
    sender_password: str
    host: str
    port: int


@dataclass(frozen=True)
class MailgunConfig:
    api_key: str
    domain: str
    sender_email: str


def require_smtp_config() -> SmtpConfig:
    """Load SMTP settings only when an SMTP adapter is actually used."""
    return SmtpConfig(
        sender_email=require_env("SENDER_EMAIL"),
        sender_password=require_env("SENDER_PASSWORD"),
        host=require_env("EMAIL_HOST"),
        port=int(require_env("EMAIL_PORT")),
    )


def require_mailgun_config() -> MailgunConfig:
    """Load and validate the sender identity verified for the Mailgun domain."""
    domain = require_env("MAILGUN_DOMAIN").lower()
    sender_email = require_env("MAILGUN_SENDER_EMAIL")
    sender_domain = sender_email.rsplit("@", 1)[-1].lower()
    if "@" not in sender_email or not (
        sender_domain == domain or sender_domain.endswith(f".{domain}")
    ):
        raise EnvironmentError(
            "[Config Error] MAILGUN_SENDER_EMAIL must belong to MAILGUN_DOMAIN."
        )
    return MailgunConfig(
        api_key=require_env("MAILGUN_API_KEY"),
        domain=domain,
        sender_email=sender_email,
    )
