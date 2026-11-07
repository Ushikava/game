from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    username: str
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    avatar_url: str | None

    class Config:
        from_attributes = True


class ChangeUsernameRequest(BaseModel):
    new_username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


class DeleteUserRequest(BaseModel):
    password: str