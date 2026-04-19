import json
import redis.asyncio as redis
from typing import Any, Optional
from IRYM_sdk.cache.base import BaseCache
from IRYM_sdk.core.config import config

class RedisCache(BaseCache):
    def __init__(self):
        self.redis = None
        self.fallback_cache = {} # In-memory fallback if Redis is down

    async def init(self):
        try:
            self.redis = redis.from_url(config.REDIS_URL, decode_responses=True)
            # Test connection
            await self.redis.ping()
        except Exception:
            self.redis = None
            print("[!] Redis connection failed. Using in-memory fallback cache.")

    async def get(self, key: str) -> Optional[Any]:
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            except Exception:
                pass
        return self.fallback_cache.get(key)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        if self.redis:
            try:
                try:
                    serialized_value = json.dumps(value)
                except TypeError:
                    serialized_value = str(value)
                await self.redis.set(key, serialized_value, ex=ttl)
                return
            except Exception:
                pass
        self.fallback_cache[key] = value

    async def delete(self, key: str) -> None:
        if self.redis:
            try:
                await self.redis.delete(key)
                return
            except Exception:
                pass
        if key in self.fallback_cache:
            del self.fallback_cache[key]
