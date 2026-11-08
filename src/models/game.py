from enum import IntEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class CloseCode(IntEnum):
    MESSAGE_TOO_BIG = 1009
    TRY_AGAIN_LATER = 1013
    UNAUTHORIZED = 4001
    REPLACED = 4002
    SESSION_REVOKED = 4003
    AUTH_TIMEOUT = 4008


class AuthMessage(BaseModel):
    type: Literal["auth"]
    token: Annotated[str, Field(min_length=1, max_length=2048)]


class PlayerInfo(BaseModel):
    id: int
    username: str
