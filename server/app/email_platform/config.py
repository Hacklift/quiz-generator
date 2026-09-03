"""Configuration shared by every email provider."""

import os


def require_sender_email() -> str:
    """Return the single configured sender identity or fail before delivery."""
    sender_email = os.getenv("SENDER_EMAIL", "").strip()
    if not sender_email:
        raise EnvironmentError(
            "[Config Error] Required environment variable 'SENDER_EMAIL' is missing."
        )
    return sender_email
