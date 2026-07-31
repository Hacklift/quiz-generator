import asyncio
import logging

from server.app.db.core.connection import get_users_collection
from server.app.users.repository import backfill_user_persona_fields


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    updated = await backfill_user_persona_fields(get_users_collection(), limit=100_000)
    logger.info("Backfilled persona on %s user records", updated)


if __name__ == "__main__":
    asyncio.run(main())
