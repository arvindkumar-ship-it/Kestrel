from collections.abc import Awaitable
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from redis.asyncio import Redis

MIN_SAMPLES = 3
LOOP_WINDOW = 4
HISTORY_TTL_SECONDS = 3600


class BehaviorFlag(StrEnum):
    NORMAL = "normal"
    TOOL_CALL_LOOP = "tool_call_loop"


@dataclass(frozen=True, slots=True)
class BehaviorResult:
    flag: BehaviorFlag
    detail: str = ""


class AgentBehaviorClassifier:
    """Detects an agent stuck calling the same tool repeatedly (a runaway/looping agent),
    from the last LOOP_WINDOW calls in its session. Below MIN_SAMPLES, always NORMAL —
    not enough history to call anything a loop yet."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def record_call(self, agent_id: str, session_id: str, tool_name: str) -> BehaviorResult:
        key = f"agent_calls:{agent_id}:{session_id}"
        await cast(Awaitable[int], self.redis.rpush(key, tool_name))
        await cast(Awaitable[str], self.redis.ltrim(key, -LOOP_WINDOW, -1))
        await self.redis.expire(key, HISTORY_TTL_SECONDS)
        history = await cast(Awaitable[list[str]], self.redis.lrange(key, 0, -1))

        if len(history) < MIN_SAMPLES:
            return BehaviorResult(BehaviorFlag.NORMAL)

        if len(history) == LOOP_WINDOW and len(set(history)) == 1:
            return BehaviorResult(
                BehaviorFlag.TOOL_CALL_LOOP,
                detail=f"{tool_name} called {len(history)}x consecutively",
            )
        return BehaviorResult(BehaviorFlag.NORMAL)
