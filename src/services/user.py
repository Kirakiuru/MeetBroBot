from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.repositories.user import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str,
    ) -> tuple[User, bool]:
        """Returns (user, is_new)."""
        user = await self.repo.get_by_telegram_id(telegram_id)

        if user is None:
            user = await self.repo.create(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
            )
            return user, True

        # Update profile if changed
        updates = {}
        if user.username != username:
            updates["username"] = username
        if user.full_name != full_name:
            updates["full_name"] = full_name

        if updates:
            user = await self.repo.update(user, **updates)

        return user, False
