from datetime import UTC, datetime, timedelta

import pytest
from app.insider.feature_store import extract_actor_features
from app.persistence.models import GraphEdge


@pytest.mark.asyncio
async def test_extract_actor_features_aggregates_per_actor(db_session):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            GraphEdge(
                actor_id="u1",
                resource_id="r1",
                resource_type="database",
                access_count=5,
                first_seen=now - timedelta(hours=2),
                last_seen=now,
            ),
            GraphEdge(
                actor_id="u1",
                resource_id="r2",
                resource_type="file",
                access_count=1,
                first_seen=now,
                last_seen=now,
            ),
            GraphEdge(
                actor_id="u2",
                resource_id="r1",
                resource_type="database",
                access_count=3,
                first_seen=now,
                last_seen=now,
            ),
        ]
    )
    await db_session.commit()

    actor_ids, matrix = await extract_actor_features(db_session)

    assert set(actor_ids) == {"u1", "u2"}
    u1_row = matrix[actor_ids.index("u1")]
    (
        resource_count,
        total_access,
        mean_access,
        max_access,
        single_ratio,
        span_hours,
        distinct_types,
    ) = u1_row

    assert resource_count == 2
    assert total_access == 6
    assert mean_access == 3
    assert max_access == 5
    assert single_ratio == 0.5
    assert span_hours == pytest.approx(2.0)
    assert distinct_types == 2


@pytest.mark.asyncio
async def test_extract_actor_features_empty_when_no_edges(db_session):
    actor_ids, matrix = await extract_actor_features(db_session)
    assert actor_ids == []
    assert matrix == []