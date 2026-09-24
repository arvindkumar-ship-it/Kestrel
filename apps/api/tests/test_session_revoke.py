import pytest

from app.response.session_revoke import SessionRevokeAdapter


@pytest.mark.asyncio
async def test_dry_run_does_not_set_redis_key(db_session, redis):
    adapter = SessionRevokeAdapter(redis, dry_run=True)
    result = await adapter.revoke_session(db_session, "sess1", "test", "tester")
    assert result.applied is False
    assert await adapter.is_session_revoked("sess1") is False


@pytest.mark.asyncio
async def test_live_mode_sets_redis_key(db_session, redis):
    adapter = SessionRevokeAdapter(redis, dry_run=False)
    result = await adapter.revoke_session(db_session, "sess2", "test", "tester")
    assert result.applied is True
    assert await adapter.is_session_revoked("sess2") is True


@pytest.mark.asyncio
async def test_idempotent_revoke_returns_already_applied(db_session, redis):
    adapter = SessionRevokeAdapter(redis, dry_run=False)
    await adapter.revoke_session(db_session, "sess3", "first", "tester")
    result = await adapter.revoke_session(db_session, "sess3", "second", "tester")
    assert result.applied is False
    assert "already" in result.reason
