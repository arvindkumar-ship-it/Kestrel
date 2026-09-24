import logging

from fastapi import HTTPException, Request, status

from app.security.api_abuse import RateAbuseDetector, SchemaDriftDetector

logger = logging.getLogger(__name__)


async def enforce_api_abuse_checks(
    request: Request,
    rate_detector: RateAbuseDetector,
    schema_detector: SchemaDriftDetector,
) -> None:
    api_key = request.headers.get("x-api-key", "anonymous")

    signal = await rate_detector.check(api_key)
    if signal and signal.confidence > 0.8:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=signal.detail)

    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.json()
        declared = getattr(request.state, "declared_schema_params", set())
        if declared:
            schema_signal = schema_detector.check(declared, set(body.keys()))
            if schema_signal and schema_signal.confidence > 0.7:
                # Soft-fail: schema drift alone is noisy (client SDK skew looks like probing) —
                # log it and let it feed the combined risk score rather than hard-blocking.
                logger.warning("schema drift", extra={"api_key": api_key, "detail": schema_signal.detail})
