import json
from typing import Any

from pydantic import ValidationError

from infrastructure.connection_manager import Connection
from schemas.game import MoveMessage
from services.movement import MovementService


class GameMessageHandler:
    def __init__(self, movement: MovementService):
        self.movement = movement

    def handle(self, connection: Connection, raw: str) -> None:
        try:
            message: Any = json.loads(raw)
        except json.JSONDecodeError:
            self.send_error(connection, "Некорректный JSON")
            return
        if not isinstance(message, dict) or not isinstance(message.get("type"), str):
            self.send_error(connection, "Сообщение должно быть объектом с полем type")
            return

        if message["type"] == "move":
            try:
                move = MoveMessage.model_validate(message)
            except ValidationError:
                self.send_error(connection, "Некорректное движение")
                return
            self.movement.move(connection, move)
            return

        self.send_error(connection, "Неизвестный тип сообщения")

    @staticmethod
    def send_error(connection: Connection, detail: str) -> None:
        connection.push({"type": "error", "detail": detail})
