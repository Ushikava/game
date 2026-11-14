from typing import Annotated

from fastapi import Depends
from fastapi.requests import HTTPConnection
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UnauthorizedError
from core.rate_limit import AuthLimits
from core.settings import settings
from db.models import User
from db.session import get_db
from infrastructure.connection_gate import ConnectionGate
from infrastructure.connection_manager import ConnectionManager
from services.auth import AuthService
from services.characters import CharacterService
from services.game_messages import GameMessageHandler
from services.game_session import GameSession, InboundLimit
from services.movement import MovementService
from services.online import OnlineService
from services.users import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_client_ip(connection: HTTPConnection) -> str:
    return connection.client.host if connection.client else "unknown"


def get_connection_manager(connection: HTTPConnection) -> ConnectionManager:
    return connection.app.state.connections


def get_connection_gate(connection: HTTPConnection) -> ConnectionGate:
    return connection.app.state.connection_gate


def get_auth_limits(connection: HTTPConnection) -> AuthLimits:
    return connection.app.state.auth_limits


ClientIp = Annotated[str, Depends(get_client_ip)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
ConnectionGateDep = Annotated[ConnectionGate, Depends(get_connection_gate)]
AuthLimitsDep = Annotated[AuthLimits, Depends(get_auth_limits)]


def limit_register(ip: ClientIp, limits: AuthLimitsDep) -> None:
    limits.register_per_ip.hit(ip)


def get_auth_service(session: DbSession, limits: AuthLimitsDep) -> AuthService:
    return AuthService(session, limits)


def get_user_service(session: DbSession, connections: ConnectionManagerDep, limits: AuthLimitsDep) -> UserService:
    return UserService(session, connections, limits)


def get_character_service(session: DbSession, connections: ConnectionManagerDep) -> CharacterService:
    return CharacterService(session, connections)


def get_online_service(connections: ConnectionManagerDep) -> OnlineService:
    return OnlineService(connections)


def get_game_session(connections: ConnectionManagerDep, gate: ConnectionGateDep, limits: AuthLimitsDep) -> GameSession:
    return GameSession(
        connections=connections,
        gate=gate,
        limits=limits,
        inbound_limit=InboundLimit(settings.ws_messages_per_second, settings.ws_message_burst),
        messages=GameMessageHandler(MovementService(connections)),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
OnlineServiceDep = Annotated[OnlineService, Depends(get_online_service)]
GameSessionDep = Annotated[GameSession, Depends(get_game_session)]


async def get_current_user(credentials: BearerCredentials, auth_service: AuthServiceDep) -> User:
    if credentials is None:
        raise UnauthorizedError()
    return await auth_service.authenticate(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
