from fastapi import HTTPException, Request, status

from app.auth import get_current_principal
from app.response.session_revoke import SessionRevokeAdapter


async def enforce_revocation_check(request: Request, revoke_adapter: SessionRevokeAdapter) -> None:
    principal = await get_current_principal(request)
    request.state.principal = principal
    session_id = principal.claims.get("sid") or principal.claims.get("jti")
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token requires sid or jti")
    if await revoke_adapter.is_session_revoked(session_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session revoked")
