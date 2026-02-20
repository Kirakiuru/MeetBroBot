"""Job: send reminders N minutes before a meeting."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.user import User
from src.database.models.vote import Vote, VoteChoice
from src.utils.text import safe

logger = logging.getLogger(__name__)


async def check_meeting_reminders(bot: Bot, sf: async_sessionmaker):
    """Send reminder N minutes before the meeting."""
    try:
        async with sf() as session:
            now = datetime.now()

            stmt = (
                select(Meeting)
                .where(
                    Meeting.status == MeetingStatus.PROPOSED,
                    Meeting.proposed_datetime.isnot(None),
                    Meeting.reminder_minutes.isnot(None),
                    Meeting.reminder_sent == False,  # noqa: E712
                )
            )
            result = await session.execute(stmt)
            meetings = result.scalars().all()

            for meeting in meetings:
                trigger_at = meeting.proposed_datetime - timedelta(
                    minutes=meeting.reminder_minutes
                )
                if now >= trigger_at:
                    await _send_meeting_reminder(bot, session, meeting)
                    meeting.reminder_sent = True

            await session.commit()
    except Exception:
        logger.exception("Error in meeting reminders job")


async def _send_meeting_reminder(bot: Bot, session: AsyncSession, meeting: Meeting):
    """Notify all YES/MAYBE voters about upcoming meeting."""
    stmt = (
        select(Vote, User)
        .join(User, Vote.user_id == User.id)
        .where(
            Vote.meeting_id == meeting.id,
            Vote.choice.in_([VoteChoice.YES, VoteChoice.MAYBE]),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return

    dt_str = meeting.proposed_datetime.strftime("%d.%m в %H:%M")
    loc = f"\n📍 {safe(meeting.location)}" if meeting.location else ""
    text = (
        f"🔔 <b>Напоминание!</b>\n\n"
        f"🎯 <b>{safe(meeting.title)}</b>\n"
        f"📅 {dt_str}{loc}\n\n"
        f"Скоро начинаемся!"
    )

    for vote, user in rows:
        try:
            await bot.send_message(chat_id=user.telegram_id, text=text)
        except Exception:
            logger.debug("Can't DM user %d", user.telegram_id)

    # Also remind in the group chat
    if meeting.chat_id:
        names = ", ".join(safe(u.full_name) for _, u in rows)
        group_text = (
            f"🔔 <b>{safe(meeting.title)}</b> скоро!\n"
            f"📅 {dt_str}{loc}\n"
            f"Идут: {names}"
        )
        try:
            await bot.send_message(chat_id=meeting.chat_id, text=group_text)
        except Exception:
            logger.debug("Can't send to chat %d", meeting.chat_id)

    logger.info("Sent meeting reminder for meeting #%d", meeting.id)
