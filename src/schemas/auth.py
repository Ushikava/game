from typing import Annotated, Literal

from pydantic import BaseModel, Field

from schemas.users import NewPassword, Password, Username

RefreshTokenValue = Annotated[str, Field(min_length=1, max_length=64)]


class RegisterRequest(BaseModel):
    username: Username
    password: NewPassword


class LoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=32, examples=["username"])]
    password: Password


class RefreshRequest(BaseModel):
    refresh_token: RefreshTokenValue


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
