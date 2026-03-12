import importlib
import os
import pytest

import server.app.email_platform.platform_email_utils as utils
from email.mime.text import MIMEText


def test_send_email_retries_and_raises(monkeypatch):
    monkeypatch.setattr(utils, 'RETRY_DELAY', 0)
    monkeypatch.setattr(utils, 'MAX_RETRIES', 2)
    calls = {"count": 0}

    def _fail(recipient, message):
        calls["count"] += 1
        raise ConnectionRefusedError(111, 'Connection refused')

    monkeypatch.setattr(utils, '_send_one', _fail)

    sleep_calls = []
    monkeypatch.setattr('time.sleep', lambda s: sleep_calls.append(s))

    msg = MIMEText('hi')
    with pytest.raises(ConnectionRefusedError):
        utils.send_email('user@example.com', msg)

    assert calls["count"] == utils.MAX_RETRIES
    assert len(sleep_calls) == utils.MAX_RETRIES - 1


def test_require_env_raises_when_missing(monkeypatch):
    # Reload module with missing env to trigger require_env behavior
    orig = os.environ.get('SENDER_EMAIL')
    monkeypatch.delenv('SENDER_EMAIL', raising=False)
    # Prevent loading values from .env during reload so missing env is detected
    monkeypatch.setattr('dotenv.load_dotenv', lambda *a, **k: None)
    # Reloading should raise EnvironmentError due to missing required var
    with pytest.raises(EnvironmentError):
        importlib.reload(utils)
    # restore environment for other tests
    if orig is not None:
        os.environ['SENDER_EMAIL'] = orig
        importlib.reload(utils)


def test_send_email_backoff_values(monkeypatch):
    monkeypatch.setattr(utils, 'RETRY_DELAY', 2)
    monkeypatch.setattr(utils, 'MAX_RETRIES', 3)
    calls = {"count": 0}

    def _fail(recipient, message):
        calls["count"] += 1
        raise ConnectionRefusedError(111, 'Connection refused')

    monkeypatch.setattr(utils, '_send_one', _fail)

    sleep_calls = []
    def _sleep(s):
        sleep_calls.append(s)

    monkeypatch.setattr('time.sleep', _sleep)

    msg = MIMEText('hi')
    with pytest.raises(ConnectionRefusedError):
        utils.send_email('user@example.com', msg)

    assert calls["count"] == utils.MAX_RETRIES
    assert len(sleep_calls) == utils.MAX_RETRIES - 1
    assert sleep_calls == [2 * 1, 2 * 2]
