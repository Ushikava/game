from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from infrastructure.connection_manager import ConnectionManager

router = APIRouter(tags=["game"])


manager = ConnectionManager()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, name: str):
    await manager.connect(name, websocket)
    await manager.send_to(name, {"type": "welcome", "online": list(manager.connections)})
    await manager.broadcast({"type": "player_joined", "name": name}, exclude=name)
    try:
        while True:
            data = await websocket.receive_json()
            print(name, "прислал:", data)
    except WebSocketDisconnect:
        manager.disconnect(name)
        await manager.broadcast({"type": "player_left", "name": name})


@router.get("/ping")
async def get_ping():
    return {"message": "pong"}

