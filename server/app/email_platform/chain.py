from .models import EmailPayload, SendResult


class ChainEmailSender:

    def __init__(self, adapters: dict[str, object]):

        self.adapters = adapters


    async def send(self, payload: EmailPayload, chain: list[str]) -> SendResult:

        last_exc = None

        for name in chain:

            try:

                res = await self.adapters[name].send(payload)

                if res.ok:

                    return res

            except Exception as e:

                last_exc = e

                continue

        raise last_exc or RuntimeError("Email chain exhausted")

