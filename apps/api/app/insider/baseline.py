import math

from redis.asyncio import Redis

KEY_PREFIX = "baseline:"


class RollingBaseline:
    """Per (actor, feature) EWMA mean/MAD baseline -> robust z-score. First sample = 0.0
    (nothing to deviate from yet); z is suppressed until n >= 5 samples exist."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def update_and_score(self, actor_id: str, feature: str, value: float) -> float:
        key = f"{KEY_PREFIX}{actor_id}:{feature}"
        raw = await self.redis.get(key)
        if raw is None:
            await self.redis.set(key, f"{value}:0:1")
            return 0.0

        mean, mad, n = (float(x) for x in raw.split(":"))
        alpha = max(0.15, 1.0 / (n + 1)) if n < 10 else 0.15
        deviation = abs(value - mean)
        new_mean = mean + alpha * (value - mean)
        new_mad = mad + alpha * (deviation - mad)
        await self.redis.set(key, f"{new_mean}:{new_mad}:{n + 1}")

        sigma = 1.4826 * new_mad
        if sigma < 1e-6 or n < 5:
            return 0.0
        return abs(value - new_mean) / sigma

    async def risk_score(self, feature_z_scores: dict[str, float]) -> float:
        if not feature_z_scores:
            return 0.0

        novelty = feature_z_scores.get("novelty", 0.0)
        rate = feature_z_scores.get("rate", 0.0)

        combined = 0.7 * novelty + 0.3 * rate

        return 1.0 / (1.0 + math.exp(-0.5 * (combined - 3.0)))