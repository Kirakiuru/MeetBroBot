from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.chat_member import ChatMember


class ChatMemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, chat_id: int, user_id: int) -> ChatMember:
        """Add user to chat. Idempotent — ignores duplicates."""
        existing = await self._get(chat_id, user_id)
        if existing:
            return existing

        member = ChatMember(chat_id=chat_id, user_id=user_id)
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove(self, chat_id: int, user_id: int) -> bool:
        stmt = delete(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_user_ids_in_chat(self, chat_id: int) -> list[int]:
        stmt = select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def remove_all_in_chat(self, chat_id: int) -> int:
        stmt = delete(ChatMember).where(ChatMember.chat_id == chat_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def _get(self, chat_id: int, user_id: int) -> ChatMember | None:
        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
