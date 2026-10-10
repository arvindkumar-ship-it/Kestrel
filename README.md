# PS-08 — Insider Threat, Anomalous Access & Autonomous Cyber Defense

Fused platform: UEBA-style insider-threat detection (log ingestion → behavior
graph → anomaly scoring) plus an AI-agent runtime guardrail (prompt-injection
/ API-abuse detection with autonomous response), sharing one alert/response
bus.

## Services

| Service | Entry point | Purpose |
|---|---|---|
| API | `uvicorn app.main:app --app-dir apps/api --port 8010` | Authenticated HTTP and WebSocket APIs |
| Stream worker | `PYTHONPATH=apps/api python -m app.worker` | Outbox relay and event consumer |
| PostgreSQL 17 | Docker Compose | Durable events, alerts and outbox |
| Redis 8 | Docker Compose | Streams, ticket redemption and revocation |

The Vite/React console is in `frontend/frontend` (`npm ci`, `npm run dev`). Its `VITE_API_BASE` defaults to `http://localhost:8010/api/v1`. Enter a configured issuer's operator/admin JWT in the console. Production requires one tenant per deployment and a trusted JWKS endpoint.

## Prerequisites

- Python 3.12
- Docker + Docker Compose
- `pip install -e ".[dev]"` for local (non-container) dev — requires a
  `pyproject.toml` with an optional `dev` extra (ruff, mypy, pytest, etc.)

## Quickstart

```bash
cp .env.example .env        # fill in real secrets — never commit .env
make up                     # builds images, starts postgres/redis/api; run the worker separately
make migrate                # alembic upgrade head (not run automatically on boot)
curl http://localhost:8001/api/v1/health/live
curl http://localhost:8001/api/v1/health/ready
```

`make down` stops everything; `make logs` tails all service logs.

## Local (non-Docker) development

```bash
make install
make migrate
uvicorn app.main:app --reload --app-dir apps/api --port 8010
# Separate terminal with the same DATABASE_URL / REDIS_URL:
PYTHONPATH=apps/api python -m app.worker
```

## Testing & quality gates

Mirrors the CI pipeline (`.github/workflows/ci.yml`):

```bash
make lint          # ruff check .
make format-check  # ruff format --check .
make typecheck      # mypy apps/api/app
make test           # pytest -q
```

Migration reversibility is checked with:

```bash
make migrate-cycle   # upgrade head -> downgrade -1 -> upgrade head
```

## Safety switches

Two independent, explicit flags gate destructive behavior — see
`.env.example`:

- `ALLOW_DRY_RUN_RESPONSES` — must be `false` in production (response mode
  must be explicit, not defaulted).
- `AUTONOMOUS_ACTIONS_ENABLED` — separate opt-in; `false` does not imply
  responses are safe, and `true` does not bypass dry-run mode.

Production startup validation additionally rejects `DEBUG=true` and a
non-HTTPS `FRONTEND_ORIGIN`.

## Secrets

Never commit `.env`. Secrets are rotated without an image rebuild. Classes
in use: `DATABASE_URL`, `REDIS_URL`/TLS credentials, JWT verification
config, websocket-ticket signing key, event-producer HMAC key, response
provider credentials, model-artifact signing key, observability exporter
credentials.

## Docker hardening

The API/worker image runs as a non-root user (uid/gid `10001`), with a
read-only root filesystem, `no-new-privileges`, and all Linux capabilities
dropped — a writable `tmpfs` is mounted at `/tmp` for anything that needs
scratch space. Workers run as separate containers/images from the API; they
are never embedded as threads inside the API process.

## Status

`docker-compose.yml`, `Makefile`, `.env.example`, and this README are the
infra scaffolding for local development. Application source
(`apps/api/app/...`) is tracked separately — see the project history for
the module-by-module build log (ingestion, graph store, detection ensemble,
response engine, observability, security tests).

Audit repair scope, reproducible checks and remaining limitations: [AUDIT_FIXES.md](AUDIT_FIXES.md).

Docker Compose exposes PostgreSQL at localhost:5434 and the API at localhost:8001. For host-run migrations/workers, set DATABASE_URL to that host port and VITE_API_BASE to the API you actually run. Authenticated simulator requests also need an operator token; the old unauthenticated simulator is not a working production ingest path.
