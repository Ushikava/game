from infrastructure.connection_manager import ConnectionManager
from schemas.game import OnlinePage


class OnlineService:
    def __init__(self, connections: ConnectionManager):
        self.connections = connections

    def get_page(self, after: int | None, limit: int) -> OnlinePage:
        players = sorted(
            (player for player in self.connections.players() if after is None or player.id > after),
            key=lambda player: player.id,
        )
        page = players[: limit + 1]
        has_more = len(page) > limit
        page = page[:limit]
        return OnlinePage(items=page, next_after=page[-1].id if has_more else None)
