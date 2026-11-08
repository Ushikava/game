import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from core.exceptions import UnauthorizedError
from db.session import SessionFactory
from infrastructure.connection_manager import Connection
from models.game import AuthMessage, CloseCode, PlayerInfo
from routers.dependencies import ConnectionManagerDep
from services.auth import AuthService

AUTH_TIMEOUT_SECONDS = 5
MAX_MESSAGE_LENGTH = 16 * 1024

router = APIRouter(tags=["game"])


class _MessageTooBigError(Exception):
    pass


@router.get("/ping")
async def get_ping() -> dict[str, str]:
    return {"message": "pong"}


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, manager: ConnectionManagerDep) -> None:
    await websocket.accept()
    player = await _authenticate(websocket)
    if player is None:
        return

    connection, replaced = await manager.connect(player, websocket)
    try:
        connection.push({"type": "welcome", "you": player.model_dump(), "online": manager.online()})
        if not replaced:
            manager.broadcast({"type": "player_joined", "player": player.model_dump()}, exclude=player.id)
        while True:
            raw = await _receive_text(websocket)
            if raw is None:
                _send_error(connection, "Ожидалось текстовое сообщение")
            else:
                _handle_message(connection, raw)
    except _MessageTooBigError:
        await connection.close(CloseCode.MESSAGE_TOO_BIG, "Сообщение слишком большое")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(connection)


async def _receive_text(websocket: WebSocket) -> str | None:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None:
        return None
    if len(text) > MAX_MESSAGE_LENGTH:
        raise _MessageTooBigError
    return text


async def _authenticate(websocket: WebSocket) -> PlayerInfo | None:
    try:
        raw = await asyncio.wait_for(_receive_text(websocket), AUTH_TIMEOUT_SECONDS)
    except TimeoutError:
        await websocket.close(CloseCode.AUTH_TIMEOUT, "Нет сообщения auth")
        return None
    except _MessageTooBigError:
        await websocket.close(CloseCode.MESSAGE_TOO_BIG, "Сообщение слишком большое")
        return None
    except WebSocketDisconnect:
        return None

    try:
        message = AuthMessage.model_validate_json(raw or "")
    except ValidationError:
        await websocket.close(CloseCode.UNAUTHORIZED, "Ожидалось сообщение auth")
        return None

    async with SessionFactory() as session:
        try:
            user = await AuthService(session).authenticate(message.token)
        except UnauthorizedError as exc:
            await websocket.close(CloseCode.UNAUTHORIZED, exc.detail)
            return None
    return PlayerInfo(id=user.id, username=user.username)


def _handle_message(connection: Connection, raw: str) -> None:
    try:
        message: Any = json.loads(raw)
    except json.JSONDecodeError:
        _send_error(connection, "Некорректный JSON")
        return
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        _send_error(connection, "Сообщение должно быть объектом с полем type")
        return
    _send_error(connection, "Неизвестный тип сообщения")


def _send_error(connection: Connection, detail: str) -> None:
    connection.push({"type": "error", "detail": detail})
