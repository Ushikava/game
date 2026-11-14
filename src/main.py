import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.exceptions import AppError, app_error_handler
from core.middleware import BodySizeLimitMiddleware
from core.rate_limit import AuthLimits
from core.settings import settings
from db.session import engine
from infrastructure.connection_gate import ConnectionGate
from infrastructure.connection_manager import ConnectionManager
from routers import auth, characters, game, users
from services.autosave import autosave_loop, save_online_positions

MAX_REQUEST_BODY_BYTES = 64 * 1024

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    connections: ConnectionManager = app.state.connections
    autosave = asyncio.create_task(autosave_loop(connections))
    yield
    autosave.cancel()
    try:
        await autosave
    except asyncio.CancelledError:
        current = asyncio.current_task()
        if current is not None and current.cancelling():
            raise
    try:
        await save_online_positions(connections)
    except Exception:
        logger.exception("Не удалось сохранить позиции при остановке сервера")
    await engine.dispose()


app = FastAPI(title="Godot/FastAPI game API", lifespan=lifespan)
app.state.connections = ConnectionManager()
app.state.connection_gate = ConnectionGate.from_settings(settings)
app.state.auth_limits = AuthLimits.from_settings(settings)

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
app.include_router(characters.router, prefix="/api")
