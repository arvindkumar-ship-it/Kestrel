import json

from redis.asyncio import Redis

from app.persistence.models import Alert

ALERT_CHANNEL = "ps08:alerts"
ALERT_STREAM = "ps08:alerts:stream"


class AlertBus:
    """Publishes alerts to Redis and persists them for dashboard queries."""

    def __init__(self, redis: Redis, session_factory) -> None:
        self.redis = redis
        self.session_factory = session_factory

    async def publish(self, alert_type: str, risk_score: float, detail: dict) -> None:
        payload = json.dumps(
            {
                "alert_type": alert_type,
                "risk_score": risk_score,
                "detail": detail,
            }
        )

        await self.redis.publish(ALERT_CHANNEL, payload)
        await self.redis.xadd(
            ALERT_STREAM,
            {"payload": payload},
            maxlen=10000,
            approximate=True,
        )

        async with self.session_factory() as session:
            session.add(
                Alert(
                    alert_type=alert_type,
                    risk_score=risk_score,
                    detail=detail,
                )
            )
            await session.commit()
