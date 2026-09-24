# PS-08 — Insider Threat, Anomalous Access & Autonomous Cyber Defense

Fused platform: UEBA-style insider-threat detection (log ingestion → behavior
graph → anomaly scoring) plus an AI-agent runtime guardrail (prompt-injection
/ API-abuse detection with autonomous response), sharing one alert/response
bus.

## Services

| Service            | Entry point                     | Purpose                                           |
|---------------------|----------------------------------|----------------------------------------------------|
| `api`               | `uvicorn app.main:app`          | FastAPI HTTP + WebSocket API                       |
| `relay`              | `python -m app.outbox_relay`    | Transactional outbox → event bus relay             |
| `detection-worker`  | `python -m app.detection_worker`| Graph/isolation-forest/ensemble scoring + alerting |
| `response-worker`   | `python -m app.response_worker` | Executes response actions (block/quarantine/revoke)|
| `postgres`          | —                                | Primary store (events, graph projection, alerts)   |
| `redis`              | —                                | Streams, pub/sub, rate windows, websocket tickets   |

Frontend (Next.js dashboard) is deployed separately; see its own env vars
below.

## Prerequisites

- Python 3.12
- Docker + Docker Compose
- `pip install -e ".[dev]"` for local (non-container) dev — requires a
  `pyproject.toml` with an optional `dev` extra (ruff, mypy, pytest, etc.)

## Quickstart

```bash
cp .env.example .env        # fill in real secrets — never commit .env
make up                     # builds images, starts postgres/redis/api/workers
make migrate                # alembic upgrade head (not run automatically on boot)
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`make down` stops everything; `make logs` tails all service logs.

## Local (non-Docker) development

```bash
make install
make migrate
uvicorn app.main:app --reload --app-dir apps/api
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
