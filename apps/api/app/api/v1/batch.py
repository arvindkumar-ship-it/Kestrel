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
