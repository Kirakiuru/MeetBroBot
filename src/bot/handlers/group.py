import logging

from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.chat_member import ChatMemberRepository

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT = """
🤝 <b>Йо! Я MeetBro.</b>

Помогу вам собраться — больше не нужно писать каждому «когда свободен?»

<b>Как работает:</b>
1. Каждый пишет мне в личку → /start → задаёт расписание
2. Здесь в группе кто-то пишет /meet
3. Я нахожу когда все свободны и предлагаю лучшее время
4. Голосуете ✅ ❌ 🤔 прямо под карточкой
5. Собрались — потусили 🎉

<b>Команды:</b>
📅 /schedule — задать своё расписание (в личке со мной)
🎯 /meet — предложить встречу (тут в группе)
ℹ️ /help — подробная справка

👉 <b>Начните с того, что каждый напишет мне в личку /start</b>
""".strip()


@router.my_chat_member(
    F.new_chat_member.status.in_({"member", "administrator"})
)
async def on_bot_added(event: ChatMemberUpdated, session: AsyncSession, bot: Bot):
    """Bot was added to a group — send welcome."""
    if event.chat.type not in ("group", "supergroup"):
        return

    logger.info(
        "Bot added to group '%s' (id=%d) by %s",
        event.chat.title,
        event.chat.id,
        event.from_user.full_name,
    )

    await bot.send_message(chat_id=event.chat.id, text=WELCOME_TEXT)


@router.my_chat_member(
    F.new_chat_member.status.in_({"left", "kicked"})
)
async def on_bot_removed(event: ChatMemberUpdated, session: AsyncSession):
    """Bot was removed from a group — clean up memberships."""
    if event.chat.type not in ("group", "supergroup"):
        return

    cm_repo = ChatMemberRepository(session)
    count = await cm_repo.remove_all_in_chat(event.chat.id)

    logger.info(
        "Bot removed from group '%s' (id=%d). Cleaned %d member records.",
        event.chat.title,
        event.chat.id,
        count,
    )
