from datetime import UTC, datetime

import pytest
import pytest_asyncio
from app.persistence import models  # noqa: F401  (registers tables on Base.metadata)
from app.persistence.database import Base
from app.persistence.models import Alert, GraphEdge
from app.streaming.alert_bus import AlertBus
from app.tasks import _run_isolation_forest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_actor(
    session_factory, actor_id: str, resource_count: int, access_count: int
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        for i in range(resource_count):
            session.add(
                GraphEdge(
                    actor_id=actor_id,
                    resource_id=f"{actor_id}-r{i}",
                    resource_type="file",
                    access_count=access_count,
                    first_seen=now,
                    last_seen=now,
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_run_isolation_forest_flags_and_publishes_outlier(session_factory, redis):
    # 9 "normal" actors: small, similar footprints.
    for i in range(9):
        await _seed_actor(
            session_factory, f"normal-{i}", resource_count=2, access_count=2
        )
    # 1 outlier: far more resources touched, far higher access volume.
    await _seed_actor(session_factory, "outlier-1", resource_count=40, access_count=200)

    alert_bus = AlertBus(redis, session_factory)
    await _run_isolation_forest(session_factory=session_factory, alert_bus=alert_bus)

    async with session_factory() as session:
        result = await session.execute(select(Alert))
        alerts = result.scalars().all()

    batch_alerts = [a for a in alerts if a.alert_type == "insider_batch_anomaly"]
    assert len(batch_alerts) >= 1
    assert batch_alerts[0].detail["actor_id"] == "outlier-1"
    assert batch_alerts[0].detail["source"] == "isolation_forest_batch"


@pytest.mark.asyncio
async def test_run_isolation_forest_noop_when_no_actors(session_factory, redis):
    alert_bus = AlertBus(redis, session_factory)

    await _run_isolation_forest(session_factory=session_factory, alert_bus=alert_bus)

    async with session_factory() as session:
        result = await session.execute(select(Alert))
        assert result.scalars().all() == []