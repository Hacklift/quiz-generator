import os
import pytest
from types import SimpleNamespace
from server.app.email_platform.models import EmailPayload

# Ensure required env vars are present before importing email modules
os.environ.setdefault("SENDER_EMAIL", "test-sender@example.com")
os.environ.setdefault("SENDER_PASSWORD", "test-password")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("ALLOWED_ORIGINS", "https://example.com")
os.environ["PRIMARY_EMAIL_PROVIDER"] = "smtp"

pytest_plugins = ["pytest_asyncio"]

class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

class FakeCeleryControl:
    def __init__(self, ping_result=True):
        self._ping_result = ping_result

    def ping(self, timeout=1):
        if isinstance(self._ping_result, Exception):
            raise self._ping_result
        return self._ping_result

class FakeCeleryApp:
    def __init__(self, ping_result=True):
        self.control = FakeCeleryControl(ping_result)
        self.sent_tasks = []

    def send_task(self, name, args=None, queue=None, ignore_result=False):
        self.sent_tasks.append({"name": name, "args": args, "queue": queue, "ignore_result": ignore_result})

@pytest.fixture(scope="function")
def fake_background_tasks():
    return FakeBackgroundTasks()

@pytest.fixture(scope="function")
def fake_celery_app():
    return FakeCeleryApp(ping_result=[{"worker": "pong"}])

@pytest.fixture(scope="function")
def fake_celery_app_unavailable():
    return FakeCeleryApp(ping_result=[])

@pytest.fixture(autouse=True)
def _base_env_and_block_network(monkeypatch):
    monkeypatch.setenv("SENDER_EMAIL", "test-sender@example.com")
    monkeypatch.setenv("SENDER_PASSWORD", "test-password")
    monkeypatch.setenv("EMAIL_HOST", "localhost")
    monkeypatch.setenv("EMAIL_PORT", "1025")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com")
    monkeypatch.setenv("PRIMARY_EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("MAILGUN_WARMUP", "0")

    class BlockedSession:
        def __init__(self, *args, **kwargs):
            self.auth = None
            self.headers = {}

        def get(self, *args, **kwargs):
            raise RuntimeError("Network calls disabled in unit tests")

        def post(self, *args, **kwargs):
            raise RuntimeError("Network calls disabled in unit tests")

    monkeypatch.setattr("requests.Session", BlockedSession)

@pytest.fixture(scope="function")
def mock_platform_send(monkeypatch):
    calls = []
    def _fake_send(recipient, message):
        calls.append((recipient, message))
    # Patch the underlying platform utils function and any adapters that imported it
    monkeypatch.setattr("server.app.email_platform.platform_email_utils.send_email", _fake_send)
    monkeypatch.setattr("server.app.email_platform.adapters.direct_adapter.send_email", _fake_send, raising=False)
    monkeypatch.setattr("server.app.email_platform.adapters.background_adapter.send_email", _fake_send, raising=False)
    return calls

@pytest.fixture(scope="function")
def mock_requests_session(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code=200, text="ok"):
            self.status_code = status_code
            self.text = text

    class FakeSession:
        def __init__(self):
            self.auth = None
            self.headers = {}
            self.last_post = None

        def get(self, url, timeout=None):
            return FakeResponse(status_code=200)

        def post(self, url, data=None):
            self.last_post = {"url": url, "data": data}
            return FakeResponse(status_code=200, text="{\"id\": \"<test>@mailgun\"}")

    monkeypatch.setattr("requests.Session", FakeSession)
    return FakeSession

@pytest.fixture(scope="function")
def email_payload_factory():
    def _factory(to="user@example.com", template_id="verification", template_vars=None):
        return EmailPayload(to=to, template_id=template_id, template_vars=template_vars or {"code": "123", "token": "abc"})
    return _factory
