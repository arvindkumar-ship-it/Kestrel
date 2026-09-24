from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccessEvent:
    actor_id: str
    resource_id: str
    resource_type: str
    occurred_at: datetime
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SecurityAlert:
    alert_type: str
    risk_score: float
    detail: dict = field(default_factory=dict)
