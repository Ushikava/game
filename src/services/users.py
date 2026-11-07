from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, ForbiddenError
from core.security import hash_password, verify_password
from db.models import User
from repositories.refresh_tokens import RefreshTokenRepository
from repositories.users import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def get_users(self) -> Sequence[User]:
        return await self.users.get_all()

    async def change_username(self, user: User, new_username: str, password: str) -> User:
        await self._ensure_password(user, password)
        user.username = new_username
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Имя пользователя уже занято") from exc
        return user

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        await self._ensure_password(user, current_password)
        user.hashed_password = await hash_password(new_password)
        await self.refresh_tokens.delete_all_for_user(user.id)
        await self.session.commit()

    async def delete_account(self, user: User, password: str) -> None:
        await self._ensure_password(user, password)
        await self.users.delete(user)
        await self.session.commit()

    async def _ensure_password(self, user: User, password: str) -> None:
        is_valid, _ = await verify_password(password, user.hashed_password)
        if not is_valid:
            raise ForbiddenError("Неверный пароль")
