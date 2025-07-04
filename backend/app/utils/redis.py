import redis.asyncio as redis
from typing import Optional

from app.core.config import settings


class RedisClient:
    _client: Optional[redis.Redis] = None
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._client
    
    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None


async def get_redis_client() -> redis.Redis:
    return await RedisClient.get_client()