from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import GraphEdge

FEATURE_NAMES = [
    "resource_count",
    "total_access_count",
    "mean_access_count",
    "max_access_count",
    "single_access_ratio",
    "span_hours",
    "distinct_resource_types",
]


async def extract_actor_features(
    session: AsyncSession,
) -> tuple[list[str], list[list[float]]]:
    """Aggregates graph_edges (durable, Postgres) per actor into a fixed-width feature
    vector for IsolationForestJob. This is the batch path — separate from the real-time
    Redis path (RollingBaseline/RateWindow) that SecurityEventHandler scores per-event.
    Order of actor_ids matches the row order of the returned matrix."""
    result = await session.execute(select(GraphEdge))
    edges = result.scalars().all()

    by_actor: dict[str, list[GraphEdge]] = {}
    for edge in edges:
        by_actor.setdefault(edge.actor_id, []).append(edge)

    actor_ids: list[str] = []
    matrix: list[list[float]] = []
    for actor_id, actor_edges in by_actor.items():
        access_counts = [e.access_count for e in actor_edges]
        resource_count = len(actor_edges)
        total_access = sum(access_counts)
        mean_access = total_access / resource_count
        max_access = max(access_counts)
        single_access_ratio = sum(1 for c in access_counts if c == 1) / resource_count
        span_seconds = (
            max(e.last_seen for e in actor_edges)
            - min(e.first_seen for e in actor_edges)
        ).total_seconds()
        span_hours = max(span_seconds, 0.0) / 3600
        distinct_types = len({e.resource_type for e in actor_edges})

        actor_ids.append(actor_id)
        matrix.append(
            [
                float(resource_count),
                float(total_access),
                mean_access,
                float(max_access),
                single_access_ratio,
                span_hours,
                float(distinct_types),
            ]
        )

    return actor_ids, matrix