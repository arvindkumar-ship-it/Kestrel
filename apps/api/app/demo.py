import asyncio
import logging
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ACTORS = [f"employee-{i}" for i in range(1, 7)]
COMMON = [(f"common-doc-{i}", "document") for i in range(1, 16)]
SENSITIVE = [
    ("payroll-database", "database"),
    ("hr-salary-export", "document"),
    ("customer-pii-db", "database"),
    ("source-code-repo", "repository"),
    ("finance-ledger", "database"),
    ("exec-comp-plan", "document"),
]

_task: asyncio.Task | None = None
_seeded = False
_used: set[tuple[str, str]] = set()


def is_running() -> bool:
    return _task is not None and not _task.done()


async def _ingest(actor: str, resource: str, rtype: str, session_factory=None) -> None:
    from app.dependencies import SessionFactory
    from app.ingestion.service import IngestionService

    async with (session_factory or SessionFactory)() as session:
        await IngestionService().ingest(
            session,
            {
                "actor_id": actor,
                "resource_id": resource,
                "resource_type": rtype,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )


async def seed_baseline(session_factory=None, graph=None) -> None:
    global _seeded
    if _seeded:
        return
    from app.dependencies import SessionFactory, get_graph_store

    graph = graph or get_graph_store()
    async with (session_factory or SessionFactory)() as session:
        for actor in ACTORS:
            for rid, rtype in COMMON:
                await graph.record_access(session, actor, rid, rtype, datetime.now(timezone.utc))
    _seeded = True


async def inject_anomaly(burst: int = 6, session_factory=None) -> dict:
    actor = random.choice(ACTORS)
    resource, rtype = random.choice(SENSITIVE)
    if (actor, resource) in _used:
        resource = f"{resource}-{random.randint(100, 999)}"
    _used.add((actor, resource))
    for _ in range(burst):
        await _ingest(actor, resource, rtype, session_factory)
        await asyncio.sleep(random.uniform(0.3, 0.8))
    return {"actor": actor, "resource": resource}


async def _loop(minutes: int) -> None:
    await seed_baseline()
    loop = asyncio.get_running_loop()
    end = loop.time() + minutes * 60
    next_anomaly = loop.time() + 10
    while loop.time() < end:
        try:
            rid, rtype = random.choice(COMMON)
            await _ingest(random.choice(ACTORS), rid, rtype)
            if loop.time() >= next_anomaly:
                await inject_anomaly()
                next_anomaly = loop.time() + random.uniform(20, 35)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("demo loop error")
        await asyncio.sleep(random.uniform(0.5, 1.5))


def start(minutes: int = 15) -> dict:
    global _task
    if not is_running():
        _task = asyncio.create_task(_loop(minutes))
    return {"running": True}


async def stop() -> dict:
    global _task
    if _task is not None:
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
        _task = None
    return {"running": False}