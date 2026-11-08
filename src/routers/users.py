from typing import Annotated

from fastapi import APIRouter, Query, status

from db.models import User
from models.users import (
    ChangePasswordRequest,
    ChangeUsernameRequest,
    DeleteAccountRequest,
    UserOut,
    UserPage,
)
from routers.dependencies import CurrentUser, UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserPage)
async def list_users(
    _: CurrentUser,
    user_service: UserServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: Annotated[int | None, Query(ge=1)] = None,
) -> UserPage:
    return await user_service.get_users(after, limit)


@router.get("/me", response_model=UserOut)
async def read_me(user: CurrentUser) -> User:
    return user


@router.patch("/me/username", response_model=UserOut)
async def change_username(body: ChangeUsernameRequest, user: CurrentUser, user_service: UserServiceDep) -> User:
    return await user_service.change_username(user, body.new_username, body.password)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordRequest, user: CurrentUser, user_service: UserServiceDep) -> None:
    await user_service.change_password(user, body.current_password, body.new_password)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(body: DeleteAccountRequest, user: CurrentUser, user_service: UserServiceDep) -> None:
    await user_service.delete_account(user, body.password)
