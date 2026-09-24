from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboxEvent(Base):
    """Transactional outbox row — written in the same DB transaction as the business write,
    relayed to the event stream by OutboxRelay. Never publish directly from a request handler."""

    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    published: Mapped[bool] = mapped_column(default=False)


class GraphEdge(Base):
    """actor --ACCESSED--> resource, with an access counter. Upserted dialect-agnostically
    (select-then-write) by GraphStore — Postgres ON CONFLICT / pg_insert breaks on SQLite tests."""

    __tablename__ = "graph_edges"
    __table_args__ = (UniqueConstraint("actor_id", "resource_id", name="uq_actor_resource"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    resource_id: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    access_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RevokedSession(Base):
    __tablename__ = "revoked_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    reason: Mapped[str] = mapped_column(String(256))
    actor: Mapped[str] = mapped_column(String(128))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_type: Mapped[str] = mapped_column(String(128))
    risk_score: Mapped[float] = mapped_column()
    detail: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
