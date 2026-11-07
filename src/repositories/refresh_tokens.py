from datetime import datetime

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, user_id: int, token_hash: str, expires_at: datetime) -> None:
        self.session.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))

    async def consume(self, token_hash: str) -> int | None:
        result = await self.session.execute(
            delete(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.expires_at > func.now())
            .returning(RefreshToken.user_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_hash(self, token_hash: str) -> None:
        await self.session.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))

    async def delete_all_for_user(self, user_id: int) -> None:
        await self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))

    async def delete_expired_for_user(self, user_id: int) -> None:
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.expires_at <= func.now())
        )
