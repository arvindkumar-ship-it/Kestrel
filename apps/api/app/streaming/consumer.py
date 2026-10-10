import asyncio
import json
import logging
import uuid

from redis.asyncio import Redis
from redis.exceptions import ResponseError

logger = logging.getLogger(__name__)
STREAM_KEY = "ps08:events:stream"
GROUP = "ps08-workers"
DEAD_LETTER_KEY = "ps08:events:dead-letter"


class EventConsumer:
    """At-least-once delivery, with pending recovery and bounded retries."""

    def __init__(self, redis: Redis, handler, *, min_idle_ms=60000, max_deliveries=5) -> None:
        self.redis = redis
        self.handler = handler
        self.consumer_name = f"worker-{uuid.uuid4()}"
        self.min_idle_ms = min_idle_ms
        self.max_deliveries = max_deliveries
        self.claim_cursor = "0-0"

    async def _ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def _process(self, message_id, fields) -> None:
        try:
            await self.handler.handle(json.loads(fields["payload"]))
            await self.redis.xack(STREAM_KEY, GROUP, message_id)
        except Exception as exc:
            logger.exception("event handling failed, message_id=%s", message_id)
            pending = await self.redis.xpending_range(STREAM_KEY, GROUP, message_id, message_id, 1)
            if pending and pending[0]["times_delivered"] >= self.max_deliveries:
                async with self.redis.pipeline(transaction=True) as pipe:
                    pipe.xadd(DEAD_LETTER_KEY, {"source_id": message_id, "payload": fields.get("payload", ""), "error_type": type(exc).__name__})
                    pipe.xack(STREAM_KEY, GROUP, message_id)
                    await pipe.execute()

    async def _recover_pending(self) -> None:
        claimed = await self.redis.xautoclaim(STREAM_KEY, GROUP, self.consumer_name, self.min_idle_ms, start_id=self.claim_cursor, count=10)
        self.claim_cursor = claimed[0]
        for message_id, fields in claimed[1]:
            await self._process(message_id, fields)

    async def consume_forever(self) -> None:
        await self._ensure_group()
        while True:
            await self._recover_pending()
            resp = await self.redis.xreadgroup(GROUP, self.consumer_name, {STREAM_KEY: ">"}, count=10, block=5000)
            for _stream, messages in resp or []:
                for message_id, fields in messages:
                    await self._process(message_id, fields)
            await asyncio.sleep(0.1)
