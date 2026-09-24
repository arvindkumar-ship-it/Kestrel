from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.persistence.models import Alert

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/alerts")
async def list_alerts(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    result = await session.execute(select(Alert).order_by(Alert.created_at.desc()).limit(100))
    return [
        {"id": a.id, "alert_type": a.alert_type, "risk_score": a.risk_score, "detail": a.detail}
        for a in result.scalars().all()
    ]
