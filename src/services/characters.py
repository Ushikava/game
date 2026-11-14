from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, ForbiddenError, NotFoundError
from db.models import Character, User
from infrastructure.connection_manager import ConnectionManager
from repositories.characters import CharacterRepository
from schemas.characters import MAX_CHARACTERS_PER_USER, CharacterList, CharacterOut
from schemas.game import CloseCode

START_POSITION = (21.0, 2.0)
BASE_HEALTH = 1000


def max_health(character: Character) -> int:
    return BASE_HEALTH


class CharacterService:
    def __init__(self, session: AsyncSession, connections: ConnectionManager):
        self.session = session
        self.connections = connections
        self.characters = CharacterRepository(session)

    async def get_characters(self, user: User) -> CharacterList:
        characters = await self.characters.list_by_user(user.id)
        return CharacterList(items=[CharacterOut.model_validate(c) for c in characters])

    async def create(self, user: User, name: str) -> Character:
        characters = await self.characters.list_by_user(user.id)
        taken_slots = {c.slot for c in characters}
        free_slots = [slot for slot in range(MAX_CHARACTERS_PER_USER) if slot not in taken_slots]
        if not free_slots:
            raise ConflictError(f"Нельзя создать больше {MAX_CHARACTERS_PER_USER} персонажей")

        x, y = START_POSITION
        try:
            character = await self.characters.add(
                user_id=user.id, slot=free_slots[0], name=name, x=x, y=y, health=BASE_HEALTH
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if await self.characters.name_taken(name):
                raise ConflictError("Имя персонажа уже занято") from exc
            raise ConflictError("Не удалось создать персонажа, попробуйте ещё раз") from exc
        return character

    async def delete(self, user: User, character_id: int, name_confirm: str) -> None:
        character = await self.characters.get_owned(character_id=character_id, user_id=user.id)
        if character is None:
            raise NotFoundError("Персонаж")
        if character.name != name_confirm:
            raise ForbiddenError("Имя персонажа введено неверно")
        await self.characters.delete(character)
        await self.session.commit()
        await self.connections.kick(user.id, CloseCode.CHARACTER_NOT_FOUND, "Персонаж удалён", character_id)

    async def get_owned(self, *, character_id: int, user_id: int) -> Character | None:
        return await self.characters.get_owned(character_id=character_id, user_id=user_id)

    async def save_positions(self, positions: Sequence[tuple[int, float, float]]) -> None:
        if not positions:
            return
        await self.characters.save_positions(positions)
        await self.session.commit()
