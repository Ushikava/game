import asyncio
import logging
from collections.abc import Sequence

from db.session import SessionFactory
from infrastructure.connection_manager import ConnectionManager
from services.characters import CharacterService

AUTOSAVE_INTERVAL_SECONDS = 30.0

logger = logging.getLogger(__name__)


async def save_positions(connections: ConnectionManager, positions: Sequence[tuple[int, float, float]]) -> None:
    async with SessionFactory() as session:
        await CharacterService(session, connections).save_positions(positions)


async def save_online_positions(connections: ConnectionManager) -> None:
    await save_positions(connections, connections.positions())


async def save_final_position(connections: ConnectionManager, position: tuple[int, float, float]) -> None:
    try:
        await save_positions(connections, [position])
    except Exception:
        logger.exception("Не удалось сохранить позицию персонажа %s", position[0])


async def autosave_loop(connections: ConnectionManager) -> None:
    while True:
        await asyncio.sleep(AUTOSAVE_INTERVAL_SECONDS)
        try:
            await save_online_positions(connections)
        except Exception:
            logger.exception("Не удалось сохранить позиции персонажей")
