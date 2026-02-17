from server.app.email_platform.service import build_email_service, EmailService
from server.app.email_platform.deps import get_email_service


class FakeBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        pass


def test_build_email_service_without_background():
    service = build_email_service(None)
    assert isinstance(service, EmailService)
    assert set(service.chain.adapters.keys()) == {"celery", "direct", "mailgun"}


def test_build_email_service_with_background():
    service = build_email_service(FakeBackgroundTasks())
    assert isinstance(service, EmailService)
    assert set(service.chain.adapters.keys()) == {"celery", "direct", "mailgun", "background"}


def test_get_email_service_includes_background():
    service = get_email_service(FakeBackgroundTasks())
    assert isinstance(service, EmailService)
    assert "background" in service.chain.adapters
