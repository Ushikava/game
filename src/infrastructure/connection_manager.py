import asyncio
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from schemas.game import CloseCode, PlayerInfo

OUTBOX_LIMIT = 256
SEND_TIMEOUT_SECONDS = 5.0
CLOSE_TIMEOUT_SECONDS = 2.0


class Connection:
    def __init__(
        self,
        user_id: int,
        player: PlayerInfo,
        position: tuple[float, float],
        websocket: WebSocket,
        on_failure: Callable[["Connection"], None],
    ) -> None:
        self.user_id: int = user_id
        self.player: PlayerInfo = player
        self.websocket: WebSocket = websocket
        self.position: tuple[float, float] = position
        self.moved_at: float = time.monotonic()
        self.move_budget: float = 0.0
        self.handed_over: bool = False
        self.closed: bool = False
        self._failed: bool = False
        self._on_failure = on_failure
        self._outbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=OUTBOX_LIMIT)
        self._sender = asyncio.create_task(self._send_loop())

    def info(self) -> dict[str, Any]:
        x, y = self.position
        return {**self.player.model_dump(), "position": {"x": x, "y": y}}

    def push(self, message: dict[str, Any]) -> None:
        if self.closed or self._failed:
            return
        try:
            self._outbox.put_nowait(message)
        except asyncio.QueueFull:
            self._fail()

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if self.closed:
            return
        self.closed = True
        self._sender.cancel()
        try:
            await self._sender
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise
        with suppress(Exception):
            await asyncio.wait_for(self.websocket.close(code, reason), CLOSE_TIMEOUT_SECONDS)

    async def _send_loop(self) -> None:
        try:
            while True:
                message = await self._outbox.get()
                await asyncio.wait_for(self.websocket.send_json(message), SEND_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._fail()

    def _fail(self) -> None:
        if self._failed:
            return
        self._failed = True
        self._on_failure(self)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, Connection] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    async def connect(
        self, user_id: int, player: PlayerInfo, position: tuple[float, float], websocket: WebSocket
    ) -> tuple[Connection, bool]:
        connection = Connection(user_id, player, position, websocket, self._on_failure)
        previous = self._connections.get(user_id)
        same_character = previous is not None and previous.player.id == player.id
        if previous is not None and same_character:
            connection.position = previous.position
            previous.handed_over = True
        if previous is not None and not same_character:
            self._forget(previous)
        self._connections[user_id] = connection
        if previous is not None:
            await previous.close(CloseCode.REPLACED, "Вход с другого устройства")
        return connection, same_character

    async def disconnect(self, connection: Connection) -> None:
        self._forget(connection)
        await connection.close()

    async def kick(self, user_id: int, code: int, reason: str, character_id: int | None = None) -> None:
        connection = self._connections.get(user_id)
        if connection is None:
            return
        if character_id is not None and connection.player.id != character_id:
            return
        self._forget(connection)
        await connection.close(code, reason)

    def online(self) -> list[dict[str, Any]]:
        return [connection.info() for connection in self._connections.values()]

    def players(self) -> list[PlayerInfo]:
        return [connection.player for connection in self._connections.values()]

    def positions(self) -> list[tuple[int, float, float]]:
        return [(c.player.id, *c.position) for c in self._connections.values()]

    def broadcast(self, message: dict[str, Any], exclude: int | None = None) -> None:
        for user_id, connection in list(self._connections.items()):
            if user_id != exclude:
                connection.push(message)

    def _on_failure(self, connection: Connection) -> None:
        self._forget(connection)
        task = asyncio.create_task(connection.close(CloseCode.TRY_AGAIN_LATER, "Соединение не успевает"))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _forget(self, connection: Connection) -> None:
        if self._connections.get(connection.user_id) is not connection:
            return
        del self._connections[connection.user_id]
        self.broadcast({"type": "player_left", "player": connection.player.model_dump()})
