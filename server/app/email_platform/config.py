"""Configuration shared by every email provider."""

import os


def require_env(var_name: str) -> str:
    """Read a required non-blank environment value without provider coupling."""
    value = os.getenv(var_name, "").strip()
    if not value:
        raise EnvironmentError(
            f"[Config Error] Required environment variable '{var_name}' is missing."
        )
    return value
