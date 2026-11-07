from fastapi import WebSocket


class ConnectionManager:
    """Хранит открытые WebSocket-соединения: имя игрока → соединение."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, name: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[name] = websocket

    def disconnect(self, name: str):
        self.connections.pop(name, None)

    async def send_to(self, name: str, message: dict):
        ws = self.connections.get(name)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict, exclude: str | None = None):
        for name, ws in list(self.connections.items()):
            if name != exclude:
                await ws.send_json(message)