import pytest

from app.insider.agent_behavior_classifier import AgentBehaviorClassifier, BehaviorFlag


@pytest.mark.asyncio
async def test_loop_detected(redis):
    clf = AgentBehaviorClassifier(redis)
    result = None
    for _ in range(4):
        result = await clf.record_call("agent1", "sess1", "read_file")
    assert result.flag == BehaviorFlag.TOOL_CALL_LOOP


@pytest.mark.asyncio
async def test_normal_sequence_no_flag_under_min_samples(redis):
    clf = AgentBehaviorClassifier(redis)
    result = await clf.record_call("agent2", "sess1", "search")
    assert result.flag == BehaviorFlag.NORMAL
