from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_revoke_adapter
from app.response.session_revoke import SessionRevokeAdapter

router = APIRouter(tags=["response"])


@router.post("/response/revoke-session")
async def revoke_session(
    session_id: str,
    reason: str,
    actor: str,
    db: AsyncSession = Depends(get_db_session),
    revoke_adapter: SessionRevokeAdapter = Depends(get_revoke_adapter),
) -> dict:
    result = await revoke_adapter.revoke_session(db, session_id, reason, actor)
    return {"applied": result.applied, "reason": result.reason}
