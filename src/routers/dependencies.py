from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UnauthorizedError
from db.models import User
from db.session import get_db
from services.auth import AuthService
from services.users import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(credentials: BearerCredentials, auth_service: AuthServiceDep) -> User:
    if credentials is None:
        raise UnauthorizedError()
    return await auth_service.authenticate(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
