from datetime import datetime, timezone

from redis.asyncio import Redis

WINDOW_SECONDS = 60


class RateWindow:
    """Fixed 60s bucket counter per actor — feeds RollingBaseline as the 'rate' feature."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def increment(self, actor_id: str) -> int:
        now = int(datetime.now(timezone.utc).timestamp())
        key = f"rate:{actor_id}:{now // WINDOW_SECONDS}"
        count = await self.redis.incr(key)
        await self.redis.expire(key, WINDOW_SECONDS * 2)
        return count
