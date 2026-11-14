import asyncio
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from core.exceptions import NotFoundError, UnauthorizedError
from core.rate_limit import AuthLimits, TokenBucket
from db.session import SessionFactory
from infrastructure.connection_gate import ConnectionGate
from infrastructure.connection_manager import ConnectionManager
from infrastructure.ws_io import MessageTooBigError, receive_text
from schemas.game import AuthMessage, CloseCode, PlayerInfo
from services.auth import AuthService
from services.autosave import save_final_position
from services.characters import CharacterService, max_health
from services.game_messages import GameMessageHandler

AUTH_TIMEOUT_SECONDS = 5
MAX_MESSAGE_LENGTH = 16 * 1024


@dataclass(frozen=True)
class WorldEntry:
    user_id: int
    player: PlayerInfo
    position: tuple[float, float]
    health: int
    max_health: int


@dataclass(frozen=True)
class InboundLimit:
    messages_per_second: float
    burst: int


class GameSession:
    def __init__(
        self,
        connections: ConnectionManager,
        gate: ConnectionGate,
        limits: AuthLimits,
        inbound_limit: InboundLimit,
        messages: GameMessageHandler,
    ):
        self.connections = connections
        self.gate = gate
        self.limits = limits
        self.inbound_limit = inbound_limit
        self.messages = messages

    async def run(self, websocket: WebSocket, ip: str) -> None:
        ticket = self.gate.enter(ip)
        await websocket.accept()
        if ticket is None:
            await websocket.close(CloseCode.TRY_AGAIN_LATER, "Сервер перегружен, попробуйте позже")
            return
        try:
            entry = await self._handshake(websocket)
            if entry is None:
                return
            self.gate.authenticated(ticket)
            await self._play(websocket, entry)
        finally:
            self.gate.leave(ticket)

    async def _handshake(self, websocket: WebSocket) -> WorldEntry | None:
        try:
            raw = await asyncio.wait_for(receive_text(websocket, MAX_MESSAGE_LENGTH), AUTH_TIMEOUT_SECONDS)
        except TimeoutError:
            await websocket.close(CloseCode.AUTH_TIMEOUT, "Нет сообщения auth")
            return None
        except MessageTooBigError:
            await websocket.close(CloseCode.MESSAGE_TOO_BIG, "Сообщение слишком большое")
            return None
        except WebSocketDisconnect:
            return None

        try:
            message = AuthMessage.model_validate_json(raw or "")
        except ValidationError:
            await websocket.close(CloseCode.UNAUTHORIZED, "Ожидалось сообщение auth")
            return None

        try:
            return await self._load_entry(message)
        except UnauthorizedError as exc:
            await websocket.close(CloseCode.UNAUTHORIZED, exc.detail)
        except NotFoundError:
            await websocket.close(CloseCode.CHARACTER_NOT_FOUND, "Персонаж не найден")
        return None

    async def _load_entry(self, message: AuthMessage) -> WorldEntry:
        async with SessionFactory() as session:
            user = await AuthService(session, self.limits).authenticate(message.token)
            character = await CharacterService(session, self.connections).get_owned(
                character_id=message.character_id, user_id=user.id
            )
        if character is None:
            raise NotFoundError("Персонаж")
        return WorldEntry(user.id, PlayerInfo(id=character.id, name=character.name), (character.x, character.y), character.health, max_health(character))  # noqa: E501

    async def _play(self, websocket: WebSocket, entry: WorldEntry) -> None:
        connection, replaced = await self.connections.connect(entry.user_id, entry.player, entry.position, entry.health, entry.max_health, websocket)  # noqa: E501
        inbound = TokenBucket(self.inbound_limit.messages_per_second, self.inbound_limit.burst)
        try:
            connection.push({"type": "welcome", "you": connection.info(), "online": self.connections.online()})
            if not replaced:
                self.connections.broadcast(
                    {"type": "player_joined", "player": connection.info()}, exclude=entry.user_id
                )
            while True:
                raw = await receive_text(websocket, MAX_MESSAGE_LENGTH)
                if not inbound.take():
                    await connection.close(CloseCode.POLICY_VIOLATION, "Слишком много сообщений")
                    return
                if raw is None:
                    self.messages.send_error(connection, "Ожидалось текстовое сообщение")
                else:
                    self.messages.handle(connection, raw)
        except MessageTooBigError:
            await connection.close(CloseCode.MESSAGE_TOO_BIG, "Сообщение слишком большое")
        except WebSocketDisconnect:
            pass
        finally:
            final_position = None if connection.handed_over else (entry.player.id, *connection.position)
            await self.connections.disconnect(connection)
            if final_position is not None:
                await save_final_position(self.connections, final_position)
