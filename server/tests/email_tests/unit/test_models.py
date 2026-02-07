import pytest
from pydantic import ValidationError

from server.app.email_platform.models import EmailPayload


def test_email_payload_invalid_email_raises():
    with pytest.raises(ValidationError):
        EmailPayload(to="not-an-email", template_id="verification", template_vars={"code": "1", "token": "t"})
