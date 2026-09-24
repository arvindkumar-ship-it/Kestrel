import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

BATCH_ALERT_THRESHOLD = 0.7
BATCH_INTERVAL_SECONDS = 3600


async def _run_isolation_forest(session_factory=None, alert_bus=None) -> dict:
    """Batch job (no Celery). Pulls per-actor feature vectors from graph_edges, scores them
    with IsolationForestJob, raises insider_batch_anomaly alerts through AlertBus for any
    actor above BATCH_ALERT_THRESHOLD. Called by the in-process loop and POST /batch/run."""
    from app.dependencies import SessionFactory, get_alert_bus
    from app.insider.feature_store import extract_actor_features
    from app.insider.isolation_forest_job import IsolationForestJob

    session_factory = session_factory or SessionFactory
    alert_bus = alert_bus or get_alert_bus()

    async with session_factory() as session:
        actor_ids, matrix = await extract_actor_features(session)

    if not actor_ids:
        logger.info("isolation_forest_batch: no actors to score")
        return {"scored": 0, "flagged": 0}

    scores = await asyncio.to_thread(IsolationForestJob().score, matrix)  # keep event loop free

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
    return {"scored": len(actor_ids), "flagged": flagged}


async def isolation_forest_loop(interval: float = BATCH_INTERVAL_SECONDS) -> None:
    """Replaces celery beat: runs the batch job every `interval` seconds."""
    while True:
        await asyncio.sleep(interval)
        try:
            await _run_isolation_forest()
        except Exception:
            logger.exception("isolation_forest_batch failed")
