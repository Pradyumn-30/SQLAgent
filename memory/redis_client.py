"""
Redis connection wrapper for persistent memory.

Sets up the connection and generic get/set/append
primitives. The agent-specific memory shape (session history, etc)
"""

import json

import redis

from config.settings import settings


class RedisMemoryClient:
    def __init__(self):
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )
        self._ttl = settings.memory_ttl_seconds

    def test_connection(self) -> bool:
        """Quick health check — used at startup to fail fast on bad config."""
        return self._client.ping()

    def get_json(self, key: str) -> dict | list | None:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set_json(self, key: str, value: dict | list, ttl: int | None = None) -> None:
        self._client.set(key, json.dumps(value), ex=ttl or self._ttl)

    def append_to_list(self, key: str, item: dict, ttl: int | None = None) -> None:
        """Append a JSON-serializable item to a Redis list, refresh TTL."""
        self._client.rpush(key, json.dumps(item))
        self._client.expire(key, ttl or self._ttl)

    def get_list(self, key: str) -> list[dict]:
        raw_items = self._client.lrange(key, 0, -1)
        return [json.loads(i) for i in raw_items]