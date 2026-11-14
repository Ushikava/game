from enum import IntEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class CloseCode(IntEnum):
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    TRY_AGAIN_LATER = 1013
    UNAUTHORIZED = 4001
    REPLACED = 4002
    SESSION_REVOKED = 4003
    CHARACTER_NOT_FOUND = 4004
    AUTH_TIMEOUT = 4008


class AuthMessage(BaseModel):
    type: Literal["auth"]
    token: Annotated[str, Field(min_length=1, max_length=2048)]
    character_id: Annotated[int, Field(ge=1, le=2**31 - 1)]


class PlayerInfo(BaseModel):
    id: int
    name: str


class OnlinePage(BaseModel):
    items: list[PlayerInfo]
    next_after: int | None


class MoveMessage(BaseModel):
    type: Literal["move"]
    x: Annotated[float, Field(allow_inf_nan=False)]
    y: Annotated[float, Field(allow_inf_nan=False)]
