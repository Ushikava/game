import math
import time

from infrastructure.connection_manager import Connection, ConnectionManager
from models.game import MoveMessage

MAX_SPEED_CELLS_PER_SECOND = 4.42

MOVE_BUDGET_MAX_CELLS = MAX_SPEED_CELLS_PER_SECOND * 0.5 + 1.0


class MovementService:
    def __init__(self, connections: ConnectionManager):
        self.connections = connections

    def move(self, connection: Connection, move: MoveMessage) -> None:
        new_position = (move.x, move.y)
        current_time = time.monotonic()
        budget = MOVE_BUDGET_MAX_CELLS
        if connection.position is not None:
            passed_time = current_time - connection.moved_at
            if passed_time < 0.05:
                return
            budget = min(connection.move_budget + MAX_SPEED_CELLS_PER_SECOND * passed_time, MOVE_BUDGET_MAX_CELLS)
            distance = math.dist(connection.position, new_position)
            if distance > budget:
                x, y = connection.position
                connection.push({"type": "position_corrected", "x": x, "y": y})
                return
            budget -= distance

        connection.position = new_position
        connection.moved_at = current_time
        connection.move_budget = budget
        self.connections.broadcast(
            {"type": "player_moved", "id": connection.player.id, "x": move.x, "y": move.y},
            exclude=connection.player.id,
        )
