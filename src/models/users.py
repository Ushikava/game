from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Username = Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[\w-]+$", examples=["username"])]
NewPassword = Annotated[str, Field(min_length=8, max_length=128, examples=["secret-password"])]
Password = Annotated[str, Field(min_length=1, max_length=128, examples=["secret-password"])]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class UserPage(BaseModel):
    items: list[UserOut]
    next_after: int | None


class ChangeUsernameRequest(BaseModel):
    new_username: Username
    password: Password


class ChangePasswordRequest(BaseModel):
    current_password: Password
    new_password: NewPassword


class DeleteAccountRequest(BaseModel):
    password: Password
