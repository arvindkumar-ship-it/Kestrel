from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.ingestion.service import IngestionService

router = APIRouter(tags=["events"])


@router.post("/events")
async def ingest_event(payload: dict, session: AsyncSession = Depends(get_db_session)) -> dict:
    await IngestionService().ingest(session, payload)
    return {"accepted": True}
