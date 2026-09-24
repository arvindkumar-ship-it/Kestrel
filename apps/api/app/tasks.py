# from celery import Celery

# from app.config import get_settings

# settings = get_settings()
# celery_app = Celery("ps08", broker=settings.redis_url, backend=settings.redis_url)


# @celery_app.task(name="app.tasks.run_isolation_forest")
# def run_isolation_forest_task() -> None:
#     """Hourly (Celery beat) batch job. Feature-vector extraction from Postgres is the one
#     piece intentionally left open here — it depends on which columns/window the actual
#     feature store ends up using; the scorer itself (IsolationForestJob) is real and tested."""
#     from app.insider.isolation_forest_job import IsolationForestJob

#     IsolationForestJob()




import asyncio
import logging

from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery("ps08", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "run-isolation-forest-hourly": {
        "task": "app.tasks.run_isolation_forest",
        "schedule": 3600.0,
    },
}

logger = logging.getLogger(__name__)

BATCH_ALERT_THRESHOLD = 0.7


@celery_app.task(name="app.tasks.run_isolation_forest")
def run_isolation_forest_task() -> None:
    """Hourly (Celery beat) batch job. Pulls per-actor feature vectors from the
    graph_edges table (extract_actor_features), scores them with the real
    IsolationForestJob, and raises an insider_batch_anomaly alert through the
    normal AlertBus for any actor whose score crosses BATCH_ALERT_THRESHOLD."""
    asyncio.run(_run_isolation_forest())


async def _run_isolation_forest(session_factory=None, alert_bus=None) -> None:
    from app.dependencies import SessionFactory, get_alert_bus
    from app.insider.feature_store import extract_actor_features
    from app.insider.isolation_forest_job import IsolationForestJob

    session_factory = session_factory or SessionFactory
    alert_bus = alert_bus or get_alert_bus()

    async with session_factory() as session:
        actor_ids, matrix = await extract_actor_features(session)

    if not actor_ids:
        logger.info("isolation_forest_batch: no actors to score")
        return

    scores = IsolationForestJob().score(matrix)

    flagged = 0
    for actor_id, score in zip(actor_ids, scores):
        if score > BATCH_ALERT_THRESHOLD:
            flagged += 1
            await alert_bus.publish(
                "insider_batch_anomaly",
                score,
                {"actor_id": actor_id, "source": "isolation_forest_batch"},
            )

    logger.info("isolation_forest_batch: scored=%d flagged=%d", len(actor_ids), flagged)