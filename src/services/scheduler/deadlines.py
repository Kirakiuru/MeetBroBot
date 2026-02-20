"""Job: warn 30 min before voting deadline."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.models.chat_member import ChatMember
from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.user import User
from src.database.models.vote import Vote
from src.utils.text import safe

logger = logging.getLogger(__name__)


async def check_deadline_reminders(bot: Bot, sf: async_sessionmaker):
    """Send reminder 30 min before voting deadline."""
    try:
        async with sf() as session:
            now = datetime.now()
            window = now + timedelta(minutes=30)

            stmt = (
                select(Meeting)
                .where(
                    Meeting.status == MeetingStatus.PROPOSED,
                    Meeting.vote_deadline.isnot(None),
                    Meeting.deadline_reminder_sent == False,  # noqa: E712
                    Meeting.vote_deadline <= window,
                    Meeting.vote_deadline > now,
                )
            )
            result = await session.execute(stmt)
            meetings = result.scalars().all()

            for meeting in meetings:
                await _send_deadline_reminder(bot, session, meeting)
                meeting.deadline_reminder_sent = True

            await session.commit()
    except Exception:
        logger.exception("Error in deadline reminders job")


async def _send_deadline_reminder(bot: Bot, session: AsyncSession, meeting: Meeting):
    """Notify the group that voting deadline is approaching."""
    if not meeting.chat_id:
        return

    # Find who hasn't voted
    cm_stmt = select(ChatMember.user_id).where(ChatMember.chat_id == meeting.chat_id)
    cm_result = await session.execute(cm_stmt)
    all_member_ids = {row[0] for row in cm_result.all()}

    vote_stmt = select(Vote.user_id).where(Vote.meeting_id == meeting.id)
    vote_result = await session.execute(vote_stmt)
    voted_ids = {row[0] for row in vote_result.all()}

    not_voted_ids = all_member_ids - voted_ids
    dl_str = meeting.vote_deadline.strftime("%H:%M")

    if not_voted_ids:
        user_stmt = select(User).where(User.id.in_(not_voted_ids))
        user_result = await session.execute(user_stmt)
        users = user_result.scalars().all()
        names = ", ".join(safe(u.full_name) for u in users)

        text = (
            f"⏰ <b>Голосование по «{safe(meeting.title)}» закроется в {dl_str}!</b>\n\n"
            f"Ещё не проголосовали: {names}"
        )
    else:
        text = (
            f"⏰ Голосование по <b>«{safe(meeting.title)}»</b> закроется в {dl_str}.\n"
            f"Все проголосовали! ✅"
        )

    try:
        await bot.send_message(chat_id=meeting.chat_id, text=text)
    except Exception:
        logger.debug("Can't send deadline reminder to chat %d", meeting.chat_id)

    logger.info("Sent deadline reminder for meeting #%d", meeting.id)
