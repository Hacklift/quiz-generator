import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from redis.asyncio import Redis, ConnectionPool
import logging
import ssl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

parsed = urlparse(REDIS_URL)
redis_kwargs = {
    "decode_responses": True,
    "max_connections": 10,
}

if parsed.scheme == "rediss":
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        redis_kwargs.update({
            "ssl_cert_reqs": ssl.CERT_REQUIRED,  
        })
    else:
        redis_kwargs.update({
            "ssl_cert_reqs": ssl.CERT_NONE, 
        })

redis_pool = ConnectionPool.from_url(REDIS_URL, **redis_kwargs)
redis = Redis(connection_pool=redis_pool)

async def get_redis_client() -> Redis:
    logger.info("Redis client acquired (pool ready)")
    return redis

async def close_redis_client() -> None:
    try:
        logger.info("Closing Redis client and connection pool")
        await redis.close()
        await redis.connection_pool.disconnect()
        logger.info("Redis connection closed successfully")
    except Exception as e:
        logger.error(f"Error closing Redis client: {e}")
