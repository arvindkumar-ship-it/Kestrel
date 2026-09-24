from datetime import datetime, timezone

from app.domain.events import AccessEvent


def normalize(raw: dict) -> AccessEvent:
    return AccessEvent(
        actor_id=str(raw["actor_id"]),
        resource_id=str(raw["resource_id"]),
        resource_type=str(raw.get("resource_type", "unknown")),
        occurred_at=(
            datetime.fromisoformat(raw["occurred_at"]) if "occurred_at" in raw else datetime.now(timezone.utc)
        ),
        metadata=raw.get("metadata", {}),
    )
