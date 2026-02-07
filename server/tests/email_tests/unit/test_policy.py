import importlib
import os

import pytest

from server.app.email_platform import policy as policy_module


def reload_policy_with_env(provider):
    os.environ["PRIMARY_EMAIL_PROVIDER"] = provider
    importlib.reload(policy_module)
    return policy_module


def test_chain_default_smtp():
    os.environ["PRIMARY_EMAIL_PROVIDER"] = "smtp"
    importlib.reload(policy_module)
    chain = policy_module.chain_for("quiz_link")
    assert chain == ["celery", "background", "mailgun"]


def test_chain_mailgun_provider():
    pm = reload_policy_with_env("mailgun")
    assert pm.chain_for("quiz_link") == ["mailgun", "celery", "background"]
    assert pm.chain_for("verification") == ["mailgun", "celery", "background", "direct"]


def test_verification_chain_default():
    os.environ["PRIMARY_EMAIL_PROVIDER"] = "smtp"
    importlib.reload(policy_module)
    assert policy_module.chain_for("verification") == ["celery", "background", "direct", "mailgun"]


def test_chain_unknown_purpose_falls_back_safely(monkeypatch):
    monkeypatch.setenv("PRIMARY_EMAIL_PROVIDER", "smtp")
    importlib.reload(policy_module)
    chain = policy_module.chain_for("non_existent_purpose")
    assert isinstance(chain, list)
    assert chain == ["celery", "background", "mailgun"]


def test_chain_unknown_provider_defaults_to_smtp(monkeypatch):
    monkeypatch.setenv("PRIMARY_EMAIL_PROVIDER", "weird")
    importlib.reload(policy_module)
    chain = policy_module.chain_for("quiz_link")
    assert chain == ["celery", "background", "mailgun"]
