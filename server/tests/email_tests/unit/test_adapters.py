import pytest
import requests

from celery.exceptions import CeleryError

from server.app.email_platform.adapters.celery_adapter import CeleryAdapter
from server.app.email_platform.adapters.background_adapter import BackgroundAdapter
from server.app.email_platform.adapters.direct_adapter import DirectAdapter
from server.app.email_platform.adapters.mailgun_adapter import MailgunAdapter
from server.app.email_platform.models import SendResult
from server.app.email_platform.renderer import render_email
from server.app.email_platform.models import EmailPayload
from server.app.email_platform import platform_email_utils as putils
from server.app.email_platform.chain import ChainEmailSender


@pytest.mark.asyncio
async def test_celery_adapter_enqueues(fake_celery_app, email_payload_factory):
    adapter = CeleryAdapter(fake_celery_app)
    payload = email_payload_factory()
    res = await adapter.send(payload)
    assert res.ok
    assert res.adapter == "celery"
    assert len(fake_celery_app.sent_tasks) == 1
    task = fake_celery_app.sent_tasks[0]
    assert task["name"] == "tasks.send_email_generic"
    assert isinstance(task["args"], list)
    assert task["args"][0] == payload.to
    expected_msg = render_email(payload.template_id, payload.to, payload.template_vars)
    assert task["args"][1] == expected_msg["Subject"]
    assert task["args"][2] == expected_msg.get_payload()
    assert task["queue"] == "email"
    assert task["ignore_result"] is True
    assert isinstance(res, SendResult)


@pytest.mark.asyncio
async def test_celery_adapter_when_no_workers(fake_celery_app_unavailable, email_payload_factory):
    adapter = CeleryAdapter(fake_celery_app_unavailable)
    payload = email_payload_factory()
    with pytest.raises(RuntimeError):
        await adapter.send(payload)


@pytest.mark.asyncio
async def test_celery_adapter_ping_raises(monkeypatch):
    class FakeCeleryControlRaise:
        def ping(self, timeout=1):
            raise CeleryError("ping failed")

    fake = type('X', (), {})()
    fake.control = FakeCeleryControlRaise()
    adapter = CeleryAdapter(fake)
    payload = EmailPayload(to="user@example.com", template_id="verification", template_vars={"code": "1", "token": "t"})
    with pytest.raises(RuntimeError) as exc:
        await adapter.send(payload)
    assert 'Celery check failed' in str(exc.value)


@pytest.mark.asyncio
async def test_celery_adapter_send_task_exception_propagates(monkeypatch):
    class FakeCeleryAppPingOk:
        def __init__(self):
            class C:
                def ping(self, timeout=1):
                    return [{"worker": "pong"}]
            self.control = C()
        def send_task(self, name, args=None, queue=None, ignore_result=False):
            raise RuntimeError("send_task failed")

    fake = FakeCeleryAppPingOk()
    adapter = CeleryAdapter(fake)
    payload = EmailPayload(to="user@example.com", template_id="verification", template_vars={"code": "1", "token": "t"})
    with pytest.raises(RuntimeError) as exc:
        await adapter.send(payload)
    assert 'send_task failed' in str(exc.value)


@pytest.mark.asyncio
async def test_background_adapter_adds_task(fake_background_tasks, email_payload_factory):
    adapter = BackgroundAdapter(fake_background_tasks)
    payload = email_payload_factory()
    res = await adapter.send(payload)
    assert res.ok
    assert res.adapter == "background"
    assert len(fake_background_tasks.tasks) == 1
    func, args, kwargs = fake_background_tasks.tasks[0]
    assert callable(func)
    assert func is putils.send_email
    assert args[0] == payload.to
    msg = args[1]
    expected = render_email(payload.template_id, payload.to, payload.template_vars)
    assert msg["Subject"] == expected["Subject"]


@pytest.mark.asyncio
async def test_direct_adapter_calls_platform_send(monkeypatch, mock_platform_send, email_payload_factory):
    adapter = DirectAdapter()
    payload = email_payload_factory()
    res = await adapter.send(payload)
    assert res.ok
    assert res.adapter == "direct"
    assert len(mock_platform_send) == 1
    assert mock_platform_send[0][0] == payload.to


@pytest.mark.asyncio
async def test_direct_adapter_propagates_smtp_error(monkeypatch, email_payload_factory):
    # make the adapter-local send_email raise an exception and ensure it propagates
    def _raise(recipient, message):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("server.app.email_platform.adapters.direct_adapter.send_email", _raise)
    adapter = DirectAdapter()
    payload = email_payload_factory()
    with pytest.raises(RuntimeError):
        await adapter.send(payload)


@pytest.mark.asyncio
async def test_mailgun_adapter_success(monkeypatch, mock_requests_session, email_payload_factory):
    monkeypatch.setenv('MAILGUN_API_KEY', 'key')
    monkeypatch.setenv('MAILGUN_DOMAIN', 'domain.test')
    adapter = MailgunAdapter()
    payload = email_payload_factory()
    res = await adapter.send(payload)
    assert isinstance(res, SendResult)
    assert res.ok
    assert res.adapter == "mailgun"
    assert hasattr(adapter.session, "last_post")
    data = adapter.session.last_post["data"]
    assert "subject" in data
    assert "to" in data
    assert data["to"][0] == payload.to
    expected = render_email(payload.template_id, payload.to, payload.template_vars)
    assert data["subject"] == expected["Subject"]
    assert expected.get_payload() in data["text"]
    assert adapter.session.auth[0] == "api"
    assert isinstance(adapter.session.auth[1], str) and len(adapter.session.auth[1]) > 0


@pytest.mark.asyncio
async def test_background_adapter_add_task_raises_and_chain_falls_back():
    class RaisingBG:
        def add_task(self, func, *args, **kwargs):
            raise RuntimeError("bg failed")

    class FakeDirect:
        async def send(self, payload):
            return SendResult(ok=True, adapter='direct')

    bg = BackgroundAdapter(RaisingBG())
    adapters = {'background': bg, 'direct': FakeDirect()}
    sender = ChainEmailSender(adapters)

    res = await sender.send(None, ['background', 'direct'])
    assert res.adapter == 'direct'


@pytest.mark.asyncio
async def test_mailgun_non_200_raises(monkeypatch):
    # Patch Session to return 500
    class FakeResp:
        def __init__(self, code=500, text='err'):
            self.status_code = code
            self.text = text

    class FakeSession:
        def __init__(self):
            self.auth = None
            self.headers = {}
        def get(self, url, timeout=None):
            return FakeResp(code=200)
        def post(self, url, data=None):
            return FakeResp(code=500, text='server error')

    monkeypatch.setattr('requests.Session', FakeSession)
    # Ensure MAILGUN_API_KEY and MAILGUN_DOMAIN are set for adapter to run
    monkeypatch.setenv('MAILGUN_API_KEY', 'key')
    monkeypatch.setenv('MAILGUN_DOMAIN', 'domain.test')
    adapter = MailgunAdapter()
    payload = EmailPayload(to='user@example.com', template_id='custom', template_vars={'subject':'hi','body':'b'})
    with pytest.raises(RuntimeError) as exc:
        await adapter.send(payload)
    assert 'server error' in str(exc.value)
    


@pytest.mark.asyncio
async def test_mailgun_request_exception_propagates(monkeypatch):
    class FakeSession2:
        def __init__(self):
            self.auth = None
            self.headers = {}
        def get(self, url, timeout=None):
            return None
        def post(self, url, data=None):
            raise requests.RequestException('network')

    monkeypatch.setattr('requests.Session', FakeSession2)
    monkeypatch.setenv('MAILGUN_API_KEY', 'key')
    monkeypatch.setenv('MAILGUN_DOMAIN', 'domain.test')

    adapter = MailgunAdapter()
    payload = EmailPayload(to='user@example.com', template_id='custom', template_vars={'subject':'hi','body':'b'})
    with pytest.raises(requests.RequestException):
        await adapter.send(payload)
