from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, UnauthorizedError
from core.rate_limit import AuthLimits, reserve
from core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from core.settings import settings
from db.models import User
from repositories.refresh_tokens import RefreshTokenRepository
from repositories.users import UserRepository
from schemas.auth import TokenPair


class AuthService:
    def __init__(self, session: AsyncSession, limits: AuthLimits):
        self.session = session
        self.limits = limits
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, username: str, password: str) -> User:
        hashed_password = await hash_password(password)
        try:
            user = await self.users.add(username, hashed_password)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Имя пользователя уже занято") from exc
        return user

    async def login(self, username: str, password: str, ip: str) -> TokenPair:
        account_ip_key = repr((username, ip))
        attempt = reserve(
            (self.limits.login_per_account_ip, account_ip_key),
            (self.limits.login_per_account, username),
            (self.limits.login_per_ip, ip),
        )
        try:
            user = await self._check_credentials(username, password)
        except UnauthorizedError:
            raise
        except BaseException:
            attempt.release()
            raise
        attempt.release()
        self.limits.login_per_account_ip.reset(account_ip_key)

        await self.refresh_tokens.delete_expired_for_user(user.id)
        tokens = self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        user_id = await self.refresh_tokens.consume(hash_refresh_token(refresh_token))
        user = await self.users.get_by_id(user_id) if user_id is not None else None
        if user is None:
            raise UnauthorizedError("Недействительный refresh-токен")

        tokens = self._issue_tokens(user)
        await self.session.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        await self.refresh_tokens.delete_by_hash(hash_refresh_token(refresh_token))
        await self.session.commit()

    async def authenticate(self, access_token: str) -> User:
        user_id, token_version = decode_access_token(access_token)
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Пользователь не найден")
        if user.token_version != token_version:
            raise UnauthorizedError("Токен отозван")
        return user

    async def _check_credentials(self, username: str, password: str) -> User:
        user = await self.users.get_by_username(username)
        password_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
        is_valid, updated_hash = await verify_password(password, password_hash)
        if user is None or not is_valid:
            raise UnauthorizedError("Неверное имя пользователя или пароль")
        if updated_hash:
            user.hashed_password = updated_hash
        return user

    def _issue_tokens(self, user: User) -> TokenPair:
        refresh_token = generate_refresh_token()
        self.refresh_tokens.add(user.id, hash_refresh_token(refresh_token), refresh_token_expires_at())
        return TokenPair(
            access_token=create_access_token(user.id, user.token_version),
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
