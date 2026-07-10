import logging
from time import perf_counter
from typing import Any


logger = logging.getLogger(__name__)


class AssistantTelemetry:
    def __init__(self, event_name: str, **metadata: Any):
        self.event_name = event_name
        self.metadata = metadata
        self.started_at = perf_counter()

    def complete(self, **metadata: Any) -> None:
        elapsed_ms = round((perf_counter() - self.started_at) * 1000, 2)
        logger.info(
            "assistant.%s completed",
            self.event_name,
            extra={"assistant": {**self.metadata, **metadata, "elapsed_ms": elapsed_ms}},
        )

    def fail(self, exc: Exception, **metadata: Any) -> None:
        elapsed_ms = round((perf_counter() - self.started_at) * 1000, 2)
        logger.warning(
            "assistant.%s failed: %s",
            self.event_name,
            exc,
            extra={"assistant": {**self.metadata, **metadata, "elapsed_ms": elapsed_ms}},
        )
