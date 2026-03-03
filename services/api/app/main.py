from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import admin, auth, downloads, games, recording_list, replay_library, subscription
from app.core.config import settings
from app.core.database import get_engine, get_session_factory

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_ANONYMOUS])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize DB connection pool and S3 client on startup; dispose on shutdown."""
    # Warm up the async engine / connection pool
    get_session_factory()
    yield
    # Dispose the engine to close all pooled connections cleanly
    engine = get_engine()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_cors_origins = (
    [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
    if settings.CORS_ALLOW_ORIGINS
    else []
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(downloads.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(subscription.router, prefix=settings.API_V1_PREFIX)
app.include_router(recording_list.router, prefix=settings.API_V1_PREFIX)
app.include_router(replay_library.router, prefix=settings.API_V1_PREFIX)
app.include_router(games.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}
