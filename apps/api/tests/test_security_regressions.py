import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from app.auth import settings
from app.middleware.api_abuse_check import enforce_api_abuse_checks
from app.middleware.revocation_check import enforce_revocation_check
from app.streaming.consumer import DEAD_LETTER_KEY, GROUP, STREAM_KEY, EventConsumer
from app.streaming.outbox_relay import OutboxRelay
from app.streaming.ws_auth import WSTicketAuth
from fastapi import HTTPException
from starlette.requests import Request


async def test_ticket_has_only_one_concurrent_redeemer(redis):
    auth = WSTicketAuth(redis)
    ticket = await auth.issue_ticket("principal")
    results = await asyncio.gather(*(auth.redeem_ticket(ticket) for _ in range(20)))
    assert sum(value == "principal" for value in results) == 1


async def test_revocation_uses_signed_session_not_optional_header(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "jwt_local_secret", "test-secret-with-at-least-32-characters")
    token = jwt.encode({"sub": "operator", "sid": "revoked-session", "roles": ["operator"], "exp": int(time.time()) + 60}, settings.jwt_local_secret, algorithm="HS256")
    request = Request({"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode()), (b"x-session-id", b"fake-session")]})
    adapter = SimpleNamespace(is_session_revoked=AsyncMock(return_value=True))
    with pytest.raises(HTTPException):
        await enforce_revocation_check(request, adapter)
    adapter.is_session_revoked.assert_awaited_once_with("revoked-session")


async def test_bodyless_post_does_not_parse_json():
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    request = Request({"type": "http", "method": "POST", "headers": []}, receive)
    await enforce_api_abuse_checks(request, SimpleNamespace(check=AsyncMock(return_value=None)), None)


async def test_publication_retry_appends_only_once(redis):
    relay = OutboxRelay(None, redis)
    row = SimpleNamespace(id=1, event_type="fixture", payload={"actor_id": "test"})
    await asyncio.gather(*(relay._publish_once(row) for _ in range(8)))
    messages = await redis.xrange(STREAM_KEY)
    assert len(messages) == 1
    assert json.loads(messages[0][1]["payload"])["event_id"] == "outbox:1"


async def test_abandoned_pending_message_is_processed(redis):
    handler = SimpleNamespace(handle=AsyncMock())
    consumer = EventConsumer(redis, handler, min_idle_ms=0)
    await consumer._ensure_group()
    await redis.xadd(STREAM_KEY, {"payload": json.dumps({"actor_id": "test"})})
    await redis.xreadgroup(GROUP, "crashed-worker", {STREAM_KEY: ">"})
    await consumer._recover_pending()
    handler.handle.assert_awaited_once_with({"actor_id": "test"})
    assert (await redis.xpending(STREAM_KEY, GROUP))["pending"] == 0


async def test_poison_message_moves_to_dead_letter(redis):
    handler = SimpleNamespace(handle=AsyncMock(side_effect=ValueError("fixture")))
    consumer = EventConsumer(redis, handler, min_idle_ms=0, max_deliveries=2)
    await consumer._ensure_group()
    await redis.xadd(STREAM_KEY, {"payload": "{}"})
    await redis.xreadgroup(GROUP, "crashed-worker", {STREAM_KEY: ">"})
    await consumer._recover_pending()
    assert len(await redis.xrange(DEAD_LETTER_KEY)) == 1
    assert (await redis.xpending(STREAM_KEY, GROUP))["pending"] == 0
