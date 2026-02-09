from redis.asyncio import Redis

from dotenv import load_dotenv

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


redis: Redis = Redis.from_url(redis_url, decode_responses=True)



async def get_redis_client() -> Redis:

    return redis


