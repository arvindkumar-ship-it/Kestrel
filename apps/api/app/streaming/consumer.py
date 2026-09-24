import asyncio
import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

STREAM_KEY = "ps08:events:stream"
GROUP = "ps08-workers"
CONSUMER_NAME = "worker-1"


class EventConsumer:
    """Consumer-group reader over the event stream. XACKs on success; leaves unacked
    entries for a future XAUTOCLAIM sweep on failure/crash recovery."""

    def __init__(self, redis: Redis, handler) -> None:
        self.redis = redis
        self.handler = handler

    async def _ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
        except Exception:
            pass  # group already exists

    async def consume_forever(self) -> None:
        await self._ensure_group()
        while True:
            resp = await self.redis.xreadgroup(GROUP, CONSUMER_NAME, {STREAM_KEY: ">"}, count=10, block=5000)
            for _stream, messages in resp or []:
                for message_id, fields in messages:
                    try:
                        await self.handler.handle(json.loads(fields["payload"]))
                        await self.redis.xack(STREAM_KEY, GROUP, message_id)
                    except Exception:
                        logger.exception("event handling failed, message_id=%s", message_id)
            await asyncio.sleep(0.1)
