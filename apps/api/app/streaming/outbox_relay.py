import asyncio
import json
import logging

from redis.exceptions import WatchError
from sqlalchemy import select

from app.persistence.models import OutboxEvent
from app.streaming.consumer import STREAM_KEY

logger = logging.getLogger(__name__)
POLL_SECONDS = 1.0
BATCH_SIZE = 100


class OutboxRelay:
    """Polls the transactional outbox table and republishes unpublished rows to the event
    stream. Business writes and outbox writes share one DB transaction; only after commit
    does this relay make them visible to the rest of the system — no dual-write gap."""

    def __init__(self, session_factory, redis) -> None:
        self.session_factory = session_factory
        self.redis = redis

    async def run_forever(self) -> None:
        while True:
            await self._relay_batch()
            await asyncio.sleep(POLL_SECONDS)

    async def _relay_batch(self) -> None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(OutboxEvent).where(OutboxEvent.published.is_(False)).order_by(OutboxEvent.id).limit(BATCH_SIZE).with_for_update(skip_locked=True)
            )
            rows = result.scalars().all()
            for row in rows:
                await self._publish_once(row)
                row.published = True
            if rows:
                await session.commit()

    async def _publish_once(self, row) -> None:
        """Append and mark atomically in Redis; retain markers during outbox replay."""
        key = f"ps08:outbox:published:{row.id}"
        payload = json.dumps({**row.payload, "event_type": row.event_type, "event_id": f"outbox:{row.id}"})
        while True:
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key)
                    if await pipe.exists(key):
                        return
                    pipe.multi()
                    pipe.xadd(STREAM_KEY, {"payload": payload})
                    pipe.set(key, "1")
                    await pipe.execute()
                    return
                except WatchError:
                    continue
