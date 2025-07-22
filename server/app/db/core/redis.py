from redis.asyncio import Redis

redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)

async def get_redis_client() -> Redis:
    return redis_client



# from redis import Redis

# def get_redis_client() -> Redis:
#     return Redis(host="localhost", port=6379, db=0, decode_responses=True)