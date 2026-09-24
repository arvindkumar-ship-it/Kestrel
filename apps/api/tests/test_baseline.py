import pytest

from app.insider.baseline import RollingBaseline


@pytest.mark.asyncio
async def test_first_sample_returns_zero(redis):
    b = RollingBaseline(redis)
    z = await b.update_and_score("actor1", "off_hours", 1.0)
    assert z == 0.0


@pytest.mark.asyncio
async def test_deviation_produces_nonzero_z(redis):
    b = RollingBaseline(redis)
    for _ in range(15):
        await b.update_and_score("actor1", "rate", 10.0)
    z = await b.update_and_score("actor1", "rate", 500.0)
    assert z > 3.0


@pytest.mark.asyncio
async def test_risk_score_bounded(redis):
    b = RollingBaseline(redis)
    score = await b.risk_score({"a": 5.0, "b": 5.0})
    assert 0.0 <= score <= 1.0
