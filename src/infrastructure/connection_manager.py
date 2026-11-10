import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from models.game import CloseCode, PlayerInfo

OUTBOX_LIMIT = 256
SEND_TIMEOUT_SECONDS = 5.0
CLOSE_TIMEOUT_SECONDS = 2.0


class Connection:
    def __init__(self, player: PlayerInfo, websocket: WebSocket, on_failure: Callable[["Connection"], None]) -> None:
        self.player: PlayerInfo = player
        self.websocket: WebSocket = websocket
        self.position: tuple[float, float] | None = None
        self.closed: bool = False
        self._failed: bool = False
        self._on_failure = on_failure
        self._outbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=OUTBOX_LIMIT)
        self._sender = asyncio.create_task(self._send_loop())

    def info(self) -> dict[str, Any]:
        if self.position is None:
            return {**self.player.model_dump(), "position": None}
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

    async def connect(self, player: PlayerInfo, websocket: WebSocket) -> tuple[Connection, bool]:
        connection = Connection(player, websocket, self._on_failure)
        previous = self._connections.get(player.id)
        self._connections[player.id] = connection
        if previous is not None:
            await previous.close(CloseCode.REPLACED, "Вход с другого устройства")
        return connection, previous is not None

    async def disconnect(self, connection: Connection) -> None:
        self._forget(connection)
        await connection.close()

    async def kick(self, user_id: int, code: int, reason: str) -> None:
        connection = self._connections.get(user_id)
        if connection is None:
            return
        self._forget(connection)
        await connection.close(code, reason)

    def online(self) -> list[dict[str, Any]]:
        return [connection.info() for connection in self._connections.values()]

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
        player = connection.player
        if self._connections.get(player.id) is not connection:
            return
        del self._connections[player.id]
        self.broadcast({"type": "player_left", "player": player.model_dump()})
