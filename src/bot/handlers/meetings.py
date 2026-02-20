from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.meeting import MeetingRepository
from src.utils.text import safe

router = Router()


@router.message(Command("meetings"))
async def cmd_meetings(message: Message, session: AsyncSession):
    """List active (PROPOSED) meetings in this chat."""
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(
            "📋 Эта команда работает в групповых чатах.\n"
            "Добавь бота в группу и используй /meetings там."
        )
        return

    meeting_repo = MeetingRepository(session)
    meetings = await meeting_repo.get_active_by_chat(message.chat.id)

    if not meetings:
        await message.answer("📭 Нет активных встреч. Создай через /meet!")
        return

    lines = ["📋 <b>Активные встречи:</b>\n"]

    for i, m in enumerate(meetings, 1):
        line = f"{i}. <b>{safe(m.title)}</b>"
        if m.proposed_datetime:
            line += f" — {m.proposed_datetime.strftime('%d.%m %H:%M')}"
        if m.location:
            line += f" 📍 {safe(m.location)}"

        vote_count = len(m.votes) if m.votes else 0
        line += f" ({vote_count} голосов)"

        # Link to pinned message if possible
        if m.message_id:
            # Telegram deep link to message in group
            chat_id = str(message.chat.id).replace("-100", "")
            line += (
                f' <a href="https://t.me/c/{chat_id}/{m.message_id}">→ перейти</a>'
            )

        lines.append(line)

    if len(meetings) == 1:
        lines.append("\n<i>Одна встреча в процессе голосования.</i>")

    await message.answer("\n".join(lines), disable_web_page_preview=True)
