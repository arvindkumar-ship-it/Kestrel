from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.tasks import _run_isolation_forest

router = APIRouter(tags=["batch"])


@router.post("/batch/run")
async def run_batch(x_batch_token: str = Header(default="")) -> dict:
    token = get_settings().batch_trigger_token
    if token and x_batch_token != token:
        raise HTTPException(403, "invalid batch token")
    return await _run_isolation_forest()


from app import demo  # noqa: E402


@router.post("/demo/start")
async def demo_start(minutes: int = 15) -> dict:
    return demo.start(min(max(minutes, 1), 60))


@router.post("/demo/stop")
async def demo_stop() -> dict:
    return await demo.stop()


@router.post("/demo/anomaly")
async def demo_anomaly() -> dict:
    return await demo.inject_anomaly()


@router.get("/demo/status")
async def demo_status() -> dict:
    return {"running": demo.is_running()}