from fastapi import WebSocket, WebSocketDisconnect


class MessageTooBigError(Exception):
    pass


async def receive_text(websocket: WebSocket, max_length: int) -> str | None:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None:
        return None
    if len(text) > max_length:
        raise MessageTooBigError
    return text
