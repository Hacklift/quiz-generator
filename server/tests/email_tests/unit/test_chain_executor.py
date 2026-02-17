import pytest

from server.app.email_platform.chain import ChainEmailSender
from server.app.email_platform.models import SendResult


class FakeAdapter:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc
        self.calls = 0

    async def send(self, payload):
        self.calls += 1
        if self._exc:
            raise self._exc
        return self._result


@pytest.mark.asyncio
async def test_chain_success_first_adapter():
    adapters = {
        "a": FakeAdapter(result=SendResult(ok=True, adapter="a")),
        "b": FakeAdapter(result=SendResult(ok=True, adapter="b")),
    }
    sender = ChainEmailSender(adapters)
    res = await sender.send(None, ["a", "b"])
    assert res.ok
    assert res.adapter == "a"
    assert adapters["a"].calls == 1
    assert adapters["b"].calls == 0


@pytest.mark.asyncio
async def test_chain_fallback_to_second_adapter():
    adapters = {
        "a": FakeAdapter(exc=RuntimeError("bad")),
        "b": FakeAdapter(result=SendResult(ok=True, adapter="b")),
    }
    sender = ChainEmailSender(adapters)
    res = await sender.send(None, ["a", "b"])
    assert res.adapter == "b"
    assert adapters["a"].calls == 1
    assert adapters["b"].calls == 1


@pytest.mark.asyncio
async def test_chain_all_fail_raises_last_exception():
    adapters = {
        "a": FakeAdapter(exc=RuntimeError("first")),
        "b": FakeAdapter(exc=ValueError("second")),
    }
    sender = ChainEmailSender(adapters)
    with pytest.raises(ValueError):
        await sender.send(None, ["a", "b"])
    assert adapters["a"].calls == 1
    assert adapters["b"].calls == 1


@pytest.mark.asyncio
async def test_chain_unknown_adapter_name_raises_keyerror():
    sender = ChainEmailSender({'a': FakeAdapter(result=SendResult(ok=True, adapter='a'))})
    with pytest.raises(KeyError):
        await sender.send(None, ['unknown'])


@pytest.mark.asyncio
async def test_adapter_returning_ok_false_continues_chain():
    adapters = {
        'a': FakeAdapter(result=SendResult(ok=False, adapter='a')),
        'b': FakeAdapter(result=SendResult(ok=True, adapter='b')),
    }
    sender = ChainEmailSender(adapters)
    res = await sender.send(None, ['a', 'b'])
    assert res.adapter == 'b'
    assert adapters['a'].calls == 1
    assert adapters['b'].calls == 1


@pytest.mark.asyncio
async def test_missing_send_attribute_raises_attributeerror():
    sender = ChainEmailSender({'a': object()})
    with pytest.raises(AttributeError):
        await sender.send(None, ['a'])
