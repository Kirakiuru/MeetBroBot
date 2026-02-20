from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.chat_member import ChatMemberRepository
from src.database.repositories.user import UserRepository


class ChatTrackerMiddleware(BaseMiddleware):
    """
    Auto-tracks which users interact in which group chats.
    Runs on every update — if it's a group message/callback,
    ensures the user is registered and linked to the chat.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Extract chat_id and user info from the event
        chat_id = None
        tg_user = None

        if isinstance(event, Message) and event.chat.type in ("group", "supergroup"):
            chat_id = event.chat.id
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat
            if chat.type in ("group", "supergroup"):
                chat_id = chat.id
                tg_user = event.from_user

        if chat_id and tg_user:
            session: AsyncSession = data.get("session")
            if session:
                # Ensure user exists
                user_repo = UserRepository(session)
                user = await user_repo.get_by_telegram_id(tg_user.id)
                if user is None:
                    user = await user_repo.create(
                        telegram_id=tg_user.id,
                        username=tg_user.username,
                        full_name=tg_user.full_name,
                    )

                # Link user ↔ chat
                cm_repo = ChatMemberRepository(session)
                await cm_repo.add(chat_id=chat_id, user_id=user.id)

        return await handler(event, data)
