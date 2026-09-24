from fastapi import HTTPException, Request, status

from app.response.session_revoke import SessionRevokeAdapter


async def enforce_revocation_check(request: Request, revoke_adapter: SessionRevokeAdapter) -> None:
    session_id = request.headers.get("x-session-id")
    if session_id and await revoke_adapter.is_session_revoked(session_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session revoked")
