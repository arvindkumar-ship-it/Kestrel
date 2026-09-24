# # import asyncio
# # import logging
# # from contextlib import asynccontextmanager

# # from fastapi import FastAPI, Request
# # from fastapi.middleware.cors import CORSMiddleware

# # from app.api.v1 import batch, dashboard, events, health, response, ws
# # from app.config import get_settings
# # from app.dependencies import close_redis, get_rate_abuse_detector, get_revoke_adapter, get_schema_drift_detector
# # from app.middleware.api_abuse_check import enforce_api_abuse_checks
# # from app.middleware.revocation_check import enforce_revocation_check
# # from app.tasks import isolation_forest_loop
# # from app.worker import run_consumer, run_relay

# # logger = logging.getLogger(__name__)
# # settings = get_settings()


# # async def _supervise(name: str, fn) -> None:
# #     while True:
# #         try:
# #             await fn()
# #         except asyncio.CancelledError:
# #             raise
# #         except Exception:
# #             logger.exception("background task %s crashed, restarting in 5s", name)
# #             await asyncio.sleep(5)


# # @asynccontextmanager
# # async def lifespan(app: FastAPI):
# #     tasks: list[asyncio.Task] = []
# #     if settings.run_workers_inline:
# #         tasks = [
# #             asyncio.create_task(_supervise("consumer", run_consumer)),
# #             asyncio.create_task(_supervise("relay", run_relay)),
# #             asyncio.create_task(_supervise("batch", isolation_forest_loop)),
# #         ]
# #     yield
# #     for t in tasks:
# #         t.cancel()
# #     await asyncio.gather(*tasks, return_exceptions=True)
# #     await close_redis()


# # app = FastAPI(title="PS08 Defense Platform", lifespan=lifespan)

# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=list({"http://localhost:5173", settings.frontend_origin}),
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # _UNAUTHENTICATED_PATHS = {"/api/v1/health/live", "/api/v1/health/ready", "/docs", "/openapi.json", "/redoc"}


# # @app.middleware("http")
# # async def security_middleware(request: Request, call_next):
# #     if request.url.path not in _UNAUTHENTICATED_PATHS:
# #         await enforce_revocation_check(request, get_revoke_adapter())
# #         await enforce_api_abuse_checks(request, get_rate_abuse_detector(), get_schema_drift_detector())
# #     return await call_next(request)


# # app.include_router(health.router, prefix="/api/v1")
# # app.include_router(events.router, prefix="/api/v1")
# # app.include_router(dashboard.router, prefix="/api/v1")
# # app.include_router(response.router, prefix="/api/v1")
# # app.include_router(batch.router, prefix="/api/v1")
# # app.include_router(ws.router, prefix="/api/v1")







# import asyncio
# import logging
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, HTTPException, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware

# from app.api.v1 import batch, dashboard, events, health, response, ws
# from app.config import get_settings
# from app.dependencies import close_redis, get_rate_abuse_detector, get_revoke_adapter, get_schema_drift_detector
# from app.middleware.api_abuse_check import enforce_api_abuse_checks
# from app.middleware.revocation_check import enforce_revocation_check
# from app.tasks import isolation_forest_loop
# from app.worker import run_consumer, run_relay

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# settings = get_settings()


# async def _supervise(name: str, fn) -> None:
#     while True:
#         try:
#             await fn()
#         except asyncio.CancelledError:
#             raise
#         except Exception:
#             logger.exception("background task %s crashed, restarting in 5s", name)
#             await asyncio.sleep(5)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     tasks: list[asyncio.Task] = []
#     if settings.run_workers_inline:
#         tasks = [
#             asyncio.create_task(_supervise("consumer", run_consumer)),
#             asyncio.create_task(_supervise("relay", run_relay)),
#             asyncio.create_task(_supervise("batch", isolation_forest_loop)),
#         ]
#     yield
#     for t in tasks:
#         t.cancel()
#     await asyncio.gather(*tasks, return_exceptions=True)
#     await close_redis()


# app = FastAPI(title="PS08 Defense Platform", lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=list({"http://localhost:5173", settings.frontend_origin}),
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# _UNAUTHENTICATED_PATHS = {"/api/v1/health/live", "/api/v1/health/ready", "/docs", "/openapi.json", "/redoc"}


# @app.middleware("http")
# async def security_middleware(request: Request, call_next):
#     if request.url.path not in _UNAUTHENTICATED_PATHS:
#         try:
#             await enforce_revocation_check(request, get_revoke_adapter())
#             await enforce_api_abuse_checks(request, get_rate_abuse_detector(), get_schema_drift_detector())
#         except HTTPException as exc:
#             return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
#     return await call_next(request)


# app.include_router(health.router, prefix="/api/v1")
# app.include_router(events.router, prefix="/api/v1")
# app.include_router(dashboard.router, prefix="/api/v1")
# app.include_router(response.router, prefix="/api/v1")
# app.include_router(batch.router, prefix="/api/v1")
# app.include_router(ws.router, prefix="/api/v1")




import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import batch, dashboard, events, health, response, ws
from app.config import get_settings
from app.dependencies import close_redis, get_rate_abuse_detector, get_revoke_adapter, get_schema_drift_detector
from app.middleware.api_abuse_check import enforce_api_abuse_checks
from app.middleware.revocation_check import enforce_revocation_check
from app.tasks import isolation_forest_loop
from app.worker import run_consumer, run_relay

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def _supervise(name: str, fn) -> None:
    while True:
        try:
            await fn()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("background task %s crashed, restarting in 5s", name)
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks: list[asyncio.Task] = []
    if settings.run_workers_inline:
        tasks = [
            asyncio.create_task(_supervise("consumer", run_consumer)),
            asyncio.create_task(_supervise("relay", run_relay)),
            asyncio.create_task(_supervise("batch", isolation_forest_loop)),
        ]
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await close_redis()


app = FastAPI(title="PS08 Defense Platform", lifespan=lifespan)


_UNAUTHENTICATED_PATHS = {"/api/v1/health/live", "/api/v1/health/ready", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path not in _UNAUTHENTICATED_PATHS:
        try:
            await enforce_revocation_check(request, get_revoke_adapter())
            await enforce_api_abuse_checks(request, get_rate_abuse_detector(), get_schema_drift_detector())
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


# added after security_middleware so CORS is outermost and also decorates 401/429 responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({"http://localhost:5173", settings.frontend_origin}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(response.router, prefix="/api/v1")
app.include_router(batch.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api/v1")