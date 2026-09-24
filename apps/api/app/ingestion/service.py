from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.normalizer import normalize
from app.ingestion.publisher import OutboxPublisher


class IngestionService:
    def __init__(self, publisher: OutboxPublisher | None = None) -> None:
        self.publisher = publisher or OutboxPublisher()

    async def ingest(self, session: AsyncSession, raw_event: dict) -> None:
        event = normalize(raw_event)
        await self.publisher.publish(session, event)
        await session.commit()
