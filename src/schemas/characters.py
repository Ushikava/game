from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

MAX_CHARACTERS_PER_USER = 5

NAME_PATTERN = r"^(?:[A-Za-z0-9]*[A-Za-z][A-Za-z0-9]*|[А-Яа-яЁё0-9]*[А-Яа-яЁё][А-Яа-яЁё0-9]*)$"

CharacterName = Annotated[str, Field(min_length=3, max_length=16, pattern=NAME_PATTERN, examples=["Ushikava"])]
CharacterNameConfirm = Annotated[str, Field(min_length=1, max_length=16, examples=["Ushikava"])]


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slot: int
    created_at: datetime


class CharacterList(BaseModel):
    items: list[CharacterOut]
    max_characters: int = MAX_CHARACTERS_PER_USER


class CreateCharacterRequest(BaseModel):
    name: CharacterName


class DeleteCharacterRequest(BaseModel):
    name: CharacterNameConfirm
