from collections.abc import Sequence

from sqlalchemy import bindparam, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Character


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: int) -> Sequence[Character]:
        result = await self.session.scalars(
            select(Character).where(Character.user_id == user_id).order_by(Character.slot)
        )
        return result.all()

    async def get_owned(self, *, character_id: int, user_id: int) -> Character | None:
        return await self.session.scalar(
            select(Character).where(Character.id == character_id, Character.user_id == user_id)
        )

    async def name_taken(self, name: str) -> bool:
        found = await self.session.scalar(select(Character.id).where(func.lower(Character.name) == name.lower()))
        return found is not None

    async def add(self, user_id: int, slot: int, name: str, x: float, y: float) -> Character:
        character = Character(user_id=user_id, slot=slot, name=name, x=x, y=y)
        self.session.add(character)
        await self.session.flush()
        return character

    async def delete(self, character: Character) -> None:
        await self.session.delete(character)
        await self.session.flush()

    async def save_positions(self, positions: Sequence[tuple[int, float, float]]) -> None:
        table = Character.__table__
        statement = update(table).where(table.c.id == bindparam("b_id")).values(x=bindparam("b_x"), y=bindparam("b_y"))
        params = [{"b_id": character_id, "b_x": x, "b_y": y} for character_id, x, y in positions]
        await self.session.execute(statement, params)
        await self.session.flush()
