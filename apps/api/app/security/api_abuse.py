import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

RATE_KEY_PREFIX = "abuse:rate:"
GEO_KEY_PREFIX = "abuse:lastseen:"
RATE_WINDOW_SECONDS = 60
RATE_Z_THRESHOLD = 3.0
IMPOSSIBLE_TRAVEL_KMH = 900  # commercial flight speed; faster = physically implausible


@dataclass
class AbuseSignal:
    signal_type: str
    confidence: float
    detail: str


class RateAbuseDetector:
    """Per-key request rate, EWMA baseline + z-score — same math as insider/baseline.py, reused."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check(self, api_key: str) -> AbuseSignal | None:
        now = int(datetime.now(timezone.utc).timestamp())
        window_key = f"{RATE_KEY_PREFIX}{api_key}:{now // RATE_WINDOW_SECONDS}"
        count = await self.redis.incr(window_key)
        await self.redis.expire(window_key, RATE_WINDOW_SECONDS * 2)

        baseline_key = f"{RATE_KEY_PREFIX}baseline:{api_key}"
        raw = await self.redis.get(baseline_key)
        if raw is None:
            await self.redis.set(baseline_key, f"{count}:0:1")
            return None

        mean, mad, n = (float(x) for x in raw.split(":"))
        alpha = max(0.15, 1.0 / (n + 1)) if n < 10 else 0.15
        deviation = abs(count - mean)
        new_mean = mean + alpha * (count - mean)
        new_mad = mad + alpha * (deviation - mad)
        await self.redis.set(baseline_key, f"{new_mean}:{new_mad}:{n + 1}")

        sigma = 1.4826 * new_mad
        if sigma < 1e-6 or n < 5:
            return None
        z = (count - new_mean) / sigma
        if z > RATE_Z_THRESHOLD:
            return AbuseSignal(
                "rate_anomaly", min(0.95, 0.5 + z * 0.1), f"z={z:.2f}, count={count}/{RATE_WINDOW_SECONDS}s"
            )
        return None


class SchemaDriftDetector:
    """Compares incoming request params against the route's declared OpenAPI schema."""

    def check(self, declared_params: set[str], actual_params: set[str]) -> AbuseSignal | None:
        unexpected = actual_params - declared_params
        if not unexpected:
            return None
        ratio = len(unexpected) / max(len(actual_params), 1)
        return AbuseSignal(
            "schema_drift",
            confidence=min(0.9, 0.4 + ratio * 0.5),
            detail=f"unexpected params: {sorted(unexpected)}",
        )


class AuthAnomalyDetector:
    """Impossible-travel + token-replay detection, per API key."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check_impossible_travel(
        self, api_key: str, lat: float, lon: float, ts: datetime
    ) -> AbuseSignal | None:
        key = f"{GEO_KEY_PREFIX}{api_key}"
        raw = await self.redis.get(key)
        await self.redis.set(key, f"{lat}:{lon}:{ts.timestamp()}", ex=86400)

        if raw is None:
            return None

        prev_lat, prev_lon, prev_ts = (float(x) for x in raw.split(":"))
        dt_hours = max((ts.timestamp() - prev_ts) / 3600, 1e-6)
        distance_km = self._haversine(prev_lat, prev_lon, lat, lon)
        speed_kmh = distance_km / dt_hours

        if speed_kmh > IMPOSSIBLE_TRAVEL_KMH:
            return AbuseSignal(
                "impossible_travel",
                confidence=0.9,
                detail=f"{distance_km:.0f}km in {dt_hours:.2f}h implies {speed_kmh:.0f}km/h",
            )
        return None

    async def check_token_replay(self, token_jti: str, expected_use_count: int = 1) -> AbuseSignal | None:
        key = f"abuse:jti:{token_jti}"
        count = await self.redis.incr(key)
        await self.redis.expire(key, 3600)
        if count > expected_use_count:
            return AbuseSignal(
                "token_replay", confidence=0.85, detail=f"jti used {count}x (expected {expected_use_count})"
            )
        return None

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))
