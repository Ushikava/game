from typing import Literal

from pydantic import BaseModel

from models.users import NewPassword, Password, Username


class RegisterRequest(BaseModel):
    username: Username
    password: NewPassword


class LoginRequest(BaseModel):
    username: str
    password: Password


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
