from functools import lru_cache

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.insider.agent_behavior_classifier import AgentBehaviorClassifier
from app.insider.baseline import RollingBaseline
from app.insider.graph_store import GraphStore
from app.insider.rate_window import RateWindow
from app.response.session_revoke import SessionRevokeAdapter
from app.security.api_abuse import AuthAnomalyDetector, RateAbuseDetector, SchemaDriftDetector
from app.streaming.alert_bus import AlertBus
from app.streaming.ws_auth import WSTicketAuth

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    await redis_client.aclose()


async def get_db_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session


@lru_cache
def get_baseline() -> RollingBaseline:
    return RollingBaseline(redis_client)


@lru_cache
def get_graph_store() -> GraphStore:
    return GraphStore(SessionFactory, redis_client)


@lru_cache
def get_rate_window() -> RateWindow:
    return RateWindow(redis_client)


@lru_cache
def get_behavior_classifier() -> AgentBehaviorClassifier:
    return AgentBehaviorClassifier(redis_client)


@lru_cache
def get_alert_bus() -> AlertBus:
    return AlertBus(redis_client, SessionFactory)


@lru_cache
def get_ws_ticket_auth() -> WSTicketAuth:
    return WSTicketAuth(redis_client, ttl_seconds=settings.websocket_ticket_ttl_seconds)


@lru_cache
def get_revoke_adapter() -> SessionRevokeAdapter:
    return SessionRevokeAdapter(redis_client, dry_run=settings.response_dry_run)


@lru_cache
def get_rate_abuse_detector() -> RateAbuseDetector:
    return RateAbuseDetector(redis_client)


@lru_cache
def get_schema_drift_detector() -> SchemaDriftDetector:
    return SchemaDriftDetector()


@lru_cache
def get_auth_anomaly_detector() -> AuthAnomalyDetector:
    return AuthAnomalyDetector(redis_client)

