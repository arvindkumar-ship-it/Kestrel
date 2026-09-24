from fastapi import FastAPI, Request

from app.api.v1 import dashboard, events, health, response, ws
from app.dependencies import close_redis, get_rate_abuse_detector, get_revoke_adapter, get_schema_drift_detector
from app.middleware.api_abuse_check import enforce_api_abuse_checks
from app.middleware.revocation_check import enforce_revocation_check
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PS08 Defense Platform")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # tumhara Vite dev origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UNAUTHENTICATED_PATHS = {"/api/v1/health/live", "/api/v1/health/ready", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path not in _UNAUTHENTICATED_PATHS:
        await enforce_revocation_check(request, get_revoke_adapter())
        await enforce_api_abuse_checks(request, get_rate_abuse_detector(), get_schema_drift_detector())
    return await call_next(request)


app.include_router(health.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(response.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()
