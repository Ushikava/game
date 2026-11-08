from typing import Annotated

from fastapi import Depends, Request
from fastapi.requests import HTTPConnection
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UnauthorizedError
from db.models import User
from db.session import get_db
from infrastructure.connection_manager import ConnectionManager
from services.auth import AuthService
from services.users import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_connection_manager(connection: HTTPConnection) -> ConnectionManager:
    return connection.app.state.connections


ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limit_login(request: Request) -> None:
    request.app.state.login_limiter.hit(_client_ip(request))


def limit_register(request: Request) -> None:
    request.app.state.register_limiter.hit(_client_ip(request))


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


def get_user_service(session: DbSession, connections: ConnectionManagerDep) -> UserService:
    return UserService(session, connections)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(credentials: BearerCredentials, auth_service: AuthServiceDep) -> User:
    if credentials is None:
        raise UnauthorizedError()
    return await auth_service.authenticate(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
