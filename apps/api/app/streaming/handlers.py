from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class SecurityEventHandler:
    def __init__(
        self,
        session_factory,
        baseline,
        graph,
        rate,
        alert_bus,
        revoke_adapter,
    ) -> None:
        self.session_factory = session_factory
        self.baseline = baseline
        self.graph = graph
        self.rate = rate
        self.alert_bus = alert_bus
        self.revoke_adapter = revoke_adapter

    async def handle(self, event: dict) -> None:
        actor_id = event.get("actor_id", "unknown")
        resource_id = event.get("resource_id", "unknown")
        resource_type = event.get("resource_type", "unknown")

        async with self.session_factory() as session:
            novelty = await self.graph.record_access(
                session,
                actor_id,
                resource_id,
                resource_type,
                datetime.now(timezone.utc),
            )

        novelty_score = self.graph.novelty_score(novelty)

        rate_count = await self.rate.increment(actor_id)
        rate_z = await self.baseline.update_and_score(
            actor_id,
            "rate",
            float(rate_count),
        )

        risk = await self.baseline.risk_score(
            {
                "novelty": novelty_score * 10,
                "rate": rate_z,
            }
        )

        logger.warning(
            "DETECTION actor=%s resource=%s novelty=%s rate_count=%s rate_z=%s risk=%s",
            actor_id,
            resource_id,
            novelty_score,
            rate_count,
            rate_z,
            risk,
        )

        if risk > 0.8:
            await self.alert_bus.publish(
                "insider_anomaly",
                risk,
                {
                    "actor_id": actor_id,
                    "resource_id": resource_id,
                    "novelty": novelty_score,
                    "rate_z": rate_z,
                },
            )
