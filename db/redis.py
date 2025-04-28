
from enum import Enum

from config import settings


use_fake_redis = False
if use_fake_redis:
    from fakeredis.aioredis import FakeRedis as Redis
else:
    from redis.asyncio import Redis



class RedisType(str, Enum):
    pass


def get_redis_client() -> Redis:
    return Redis(
        host=settings.redis_ip,
        port=settings.redis_port,
        db=0,
        decode_responses=True
    )