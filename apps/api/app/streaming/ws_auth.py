import secrets

from redis.asyncio import Redis

TICKET_PREFIX = "ws:ticket:"


class WSTicketAuth:
    """Short-lived, single-use websocket tickets — avoids putting long-lived JWTs in a
    query string where they'd land in access logs / browser history."""

    def __init__(self, redis: Redis, ttl_seconds: int = 60) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def issue_ticket(self, principal_id: str) -> str:
        ticket = secrets.token_urlsafe(32)
        await self.redis.set(f"{TICKET_PREFIX}{ticket}", principal_id, ex=self.ttl_seconds)
        return ticket

    async def redeem_ticket(self, ticket: str) -> str | None:
        key = f"{TICKET_PREFIX}{ticket}"
        principal_id = await self.redis.get(key)
        if principal_id is not None:
            await self.redis.delete(key)  # single-use
        return principal_id
