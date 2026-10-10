# Authentication and stream reliability

Repair branch: `fix/internship-audit-20261010`. Changes are scoped to audit findings; no deployment or live provider action is included.

## Changed

Operator APIs now require verified operator/admin JWTs. Response actor comes from the token; session revocation uses signed sid/jti. Production is explicitly one tenant per deployment and requires a tenant ID and JWKS. WebSocket tickets are atomically consumed once. Bodyless requests work; malformed JSON is rejected. Outbox events have stable IDs and a Redis transaction marker, pending messages are reclaimed, and poison messages enter a bounded dead-letter queue. The console accepts a JWT in memory and supplies it to protected APIs.

## Verification

`pytest -q; mypy apps/api/app; cd frontend/frontend && npm ci && npm run build`

Commands are entry points, not a claim that every live integration was executed. See the repair bundle for actual results.

## Setup and remaining evidence

Start PostgreSQL 17 and Redis 8, install -e ".[dev]", run alembic upgrade head, then PYTHONPATH=apps/api uvicorn app.main:app --port 8010 and separately PYTHONPATH=apps/api python -m app.worker. Public health paths are /api/v1/health/live and /api/v1/health/ready. Local/test tokens must use JWT_LOCAL_SECRET and include sub, sid or jti, exp, and roles=["operator"]; use a trusted issuer in production. Consumers are at-least-once: a crash after handler effects and before acknowledgement can repeat those effects. Handler-level durable idempotency, PostgreSQL concurrent-worker integration, real enforcement adapters and detector calibration remain open. Redis outbox markers must be retained as long as PostgreSQL rows can replay. Existing whole-repo lint/format failures in unrelated historical tests/simulator are recorded, not silently suppressed.
