from datetime import datetime, timezone

import pytest

from app.security.api_abuse import AuthAnomalyDetector, RateAbuseDetector, SchemaDriftDetector


@pytest.mark.asyncio
async def test_rate_abuse_no_signal_below_threshold(redis):
    d = RateAbuseDetector(redis)
    signal = await d.check("key1")
    assert signal is None


def test_schema_drift_flags_unexpected_params():
    d = SchemaDriftDetector()
    signal = d.check(declared_params={"a", "b"}, actual_params={"a", "b", "c"})
    assert signal is not None
    assert signal.signal_type == "schema_drift"


def test_schema_drift_no_signal_when_clean():
    d = SchemaDriftDetector()
    assert d.check(declared_params={"a", "b"}, actual_params={"a", "b"}) is None


@pytest.mark.asyncio
async def test_impossible_travel_flags_implausible_speed(redis):
    d = AuthAnomalyDetector(redis)
    t0 = datetime.now(timezone.utc)
    await d.check_impossible_travel("key1", 40.7128, -74.0060, t0)  # New York
    t1 = t0.replace(minute=(t0.minute + 1) % 60)
    signal = await d.check_impossible_travel("key1", 35.6762, 139.6503, t1)  # Tokyo, 1 min later
    assert signal is not None
    assert signal.signal_type == "impossible_travel"


@pytest.mark.asyncio
async def test_token_replay_flags_second_use(redis):
    d = AuthAnomalyDetector(redis)
    first = await d.check_token_replay("jti1")
    second = await d.check_token_replay("jti1")
    assert first is None
    assert second is not None
    assert second.signal_type == "token_replay"
