from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import AccessEvent
from app.persistence.models import OutboxEvent


class OutboxPublisher:
    """Writes to the outbox table in the same transaction as the business write — never
    publishes directly to Redis from a request handler (that's the relay's job)."""

    async def publish(self, session: AsyncSession, event: AccessEvent) -> None:
        session.add(
            OutboxEvent(
                event_type="access_event",
                payload={
                    "actor_id": event.actor_id,
                    "resource_id": event.resource_id,
                    "resource_type": event.resource_type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "metadata": event.metadata,
                },
            )
        )
