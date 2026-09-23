"""Regression checks for imports that must work in a fresh server process."""

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_server_module_imports_in_a_clean_interpreter():
    """Catch cycles hidden by pytest's shared module-import order."""
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
            "JWT_SECRET": "test-secret",
            "ASSISTANT_INTERNAL_MCP_SECRET": "test-mcp-secret",
            "email_sender": "test@example.com",
            "email_password": "test-password",
            "email_host": "localhost",
            "email_port": "1025",
            "share_url": "http://localhost:3000",
            "db_name": "quizApp_db",
            "MONGO_URI": "mongodb://localhost:27017",
            "REDIS_URL": "redis://localhost:6379/0",
            "MAILGUN_API_KEY": "test-key",
            "MAILGUN_DOMAIN": "example.com",
            "MAILGUN_SENDER_EMAIL": "no-reply@example.com",
        }
    )

    result = subprocess.run(
        [sys.executable, "-c", "import server.main"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
