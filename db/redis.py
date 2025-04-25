
from enum import Enum
from redis.asyncio import Redis
from config import settings


class RedisType(str, Enum):
    pass


def get_redis_client() -> Redis:
    return Redis(
        host=settings.redis_ip,
        port=settings.redis_port,
        db=0,
        decode_responses=True
    )