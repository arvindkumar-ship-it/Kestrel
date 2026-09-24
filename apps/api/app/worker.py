import asyncio
import logging

from app.dependencies import (
    SessionFactory,
    close_redis,
    get_alert_bus,
    get_baseline,
    get_graph_store,
    get_rate_window,
    get_revoke_adapter,
    redis_client,
)
from app.streaming.consumer import EventConsumer
from app.streaming.handlers import SecurityEventHandler
from app.streaming.outbox_relay import OutboxRelay

logging.basicConfig(level=logging.INFO)


async def run_consumer() -> None:
    handler = SecurityEventHandler(
        session_factory=SessionFactory,
        baseline=get_baseline(),
        graph=get_graph_store(),
        rate=get_rate_window(),
        alert_bus=get_alert_bus(),
        revoke_adapter=get_revoke_adapter(),
    )
    consumer = EventConsumer(redis=redis_client, handler=handler)
    await consumer.consume_forever()


async def run_relay() -> None:
    relay = OutboxRelay(session_factory=SessionFactory, redis=redis_client)
    await relay.run_forever()


async def main() -> None:
    try:
        await asyncio.gather(run_consumer(), run_relay())
    finally:
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
