from dataclasses import dataclass
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import RevokedSession

REVOKE_KEY_PREFIX = "session:revoked:"


@dataclass(frozen=True, slots=True)
class RevokeResult:
    applied: bool
    reason: str


class SessionRevokeAdapter:
    """Autonomous-response action: revoke a session. dry_run=True (default) never mutates
    state — matches ALLOW_DRY_RUN_RESPONSES being the safe default; production must flip
    RESPONSE_DRY_RUN explicitly."""

    def __init__(self, redis: Redis, dry_run: bool = True) -> None:
        self.redis = redis
        self.dry_run = dry_run

    async def is_session_revoked(self, session_id: str) -> bool:
        return await self.redis.exists(f"{REVOKE_KEY_PREFIX}{session_id}") == 1

    async def revoke_session(
        self, session: AsyncSession, session_id: str, reason: str, actor: str
    ) -> RevokeResult:
        if await self.is_session_revoked(session_id):
            return RevokeResult(applied=False, reason=f"session {session_id} already revoked")

        if self.dry_run:
            return RevokeResult(applied=False, reason="dry_run: no action taken")

        await self.redis.set(f"{REVOKE_KEY_PREFIX}{session_id}", reason)
        session.add(
            RevokedSession(
                session_id=session_id, reason=reason, actor=actor, revoked_at=datetime.now(timezone.utc)
            )
        )
        await session.commit()
        return RevokeResult(applied=True, reason=reason)
