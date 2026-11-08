from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.exceptions import AppError, app_error_handler
from core.middleware import BodySizeLimitMiddleware
from core.rate_limit import RateLimiter
from core.settings import settings
from db.session import engine
from infrastructure.connection_manager import ConnectionManager
from routers import auth, game, users

MAX_REQUEST_BODY_BYTES = 64 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="Godot/FastAPI game API", lifespan=lifespan)
app.state.connections = ConnectionManager()
app.state.login_limiter = RateLimiter(settings.login_rate_limit, settings.login_rate_window_seconds)
app.state.register_limiter = RateLimiter(settings.register_rate_limit, settings.register_rate_window_seconds)

app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_REQUEST_BODY_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)

app.include_router(game.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
