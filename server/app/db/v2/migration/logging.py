import json
import logging


logger = logging.getLogger(__name__)


def log_migration_event(event: str, **fields):
    logger.info("%s | %s", event, json.dumps(fields, default=str, sort_keys=True))
