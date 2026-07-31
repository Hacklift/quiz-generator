import os

os.environ.setdefault("ASSISTANT_INTERNAL_MCP_SECRET", "test-internal-mcp-secret")

# email_platform reads these at import time, so any test importing
# users.services (or anything downstream of it) needs them set before
# collection. Values match server/tests/email_tests/conftest.py, whose
# renderer tests assert on the sender address.
os.environ.setdefault("SENDER_EMAIL", "test-sender@example.com")
os.environ.setdefault("SENDER_PASSWORD", "test-password")
