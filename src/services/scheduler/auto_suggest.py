"""Job: auto-suggest meetings when 3+ people have overlapping availability."""

import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.database.models.chat_member import ChatMember
from src.database.repositories.meeting import MeetingRepository
from src.services.scheduling import SchedulingService
from src.utils.text import safe

logger = logging.getLogger(__name__)


async def auto_suggest_meetings(bot: Bot, sf: async_sessionmaker):
    """
    Once a day, check each group chat for strong availability overlaps.
    If 3+ people are all free at the same time — suggest a meetup.
    Only suggests if there's no active (PROPOSED) meeting in that chat.
    """
    try:
        async with sf() as session:
            chat_stmt = select(ChatMember.chat_id).distinct()
            chat_result = await session.execute(chat_stmt)
            chat_ids = [row[0] for row in chat_result.all()]

            repo = MeetingRepository(session)
            scheduling = SchedulingService(session)

            for chat_id in chat_ids:
                active = await repo.get_active_by_chat(chat_id)
                if active:
                    continue

                member_stmt = select(ChatMember.user_id).where(
                    ChatMember.chat_id == chat_id
                )
                member_result = await session.execute(member_stmt)
                user_ids = [row[0] for row in member_result.all()]

                if len(user_ids) < 2:
                    continue

                suggestions = await scheduling.find_best_slots(user_ids, days_ahead=7)
                if not suggestions:
                    continue

                best = suggestions[0]
                if best["count"] < 3:
                    continue

                DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                day_name = DAYS[best["date"].weekday()]
                names_str = ", ".join(safe(n) for n in best["names"])
                text = (
                    f"💡 <b>Идея для встречи!</b>\n\n"
                    f"📅 <b>{day_name} {best['date'].strftime('%d.%m')}</b> "
                    f"{best['start'].strftime('%H:%M')}–{best['end'].strftime('%H:%M')}\n"
                    f"👥 Свободны ({best['count']}): {names_str}\n\n"
                    f"Создайте встречу → /meet"
                )

                try:
                    await bot.send_message(chat_id=chat_id, text=text)
                    logger.info("Auto-suggested meeting in chat %d", chat_id)
                except Exception:
                    logger.debug("Can't send auto-suggest to chat %d", chat_id)
    except Exception:
        logger.exception("Error in auto-suggest job")
