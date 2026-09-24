from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import GraphEdge


@dataclass(frozen=True, slots=True)
class NoveltyResult:
    is_new_edge: bool
    actor_resource_count: int
    resource_degree: int


class GraphStore:
    """actor<->resource access graph. record_access is a dialect-agnostic upsert
    (select-then-write) — deliberately NOT pg_insert().on_conflict_do_update(), which is
    Postgres-only and breaks on the SQLite engine used in tests."""

    def __init__(self, session_factory, redis) -> None:
        self.session_factory = session_factory
        self.redis = redis

    async def record_access(
        self,
        session: AsyncSession,
        actor_id: str,
        resource_id: str,
        resource_type: str,
        ts: datetime,
    ) -> NoveltyResult:
        result = await session.execute(
            select(GraphEdge).where(
                GraphEdge.actor_id == actor_id,
                GraphEdge.resource_id == resource_id,
            )
        )
        edge = result.scalar_one_or_none()
        is_new = edge is None
        if edge is None:
            edge = GraphEdge(
                actor_id=actor_id,
                resource_id=resource_id,
                resource_type=resource_type,
                access_count=1,
                first_seen=ts,
                last_seen=ts,
            )
            session.add(edge)
        else:
            edge.access_count += 1
            edge.last_seen = ts
        await session.commit()

        actor_edges = await session.execute(select(GraphEdge).where(GraphEdge.actor_id == actor_id))
        actor_resource_count = len(actor_edges.scalars().all())

        resource_edges = await session.execute(
            select(GraphEdge).where(GraphEdge.resource_id == resource_id)
        )
        resource_degree = len(resource_edges.scalars().all())

        return NoveltyResult(is_new, actor_resource_count, resource_degree)

    @staticmethod
    def novelty_score(result: NoveltyResult) -> float:
        if not result.is_new_edge:
            return 0.0
        # Rarer resource (lower degree) -> higher novelty/risk.
        return max(0.0, 1.0 - (result.resource_degree - 1) * 0.2)
