from fastapi import APIRouter, WebSocket

from routers.dependencies import ClientIp, GameSessionDep

router = APIRouter(tags=["game"])


@router.get("/ping")
async def get_ping() -> dict[str, str]:
    return {"message": "pong"}


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, ip: ClientIp, game_session: GameSessionDep) -> None:
    await game_session.run(websocket, ip)
