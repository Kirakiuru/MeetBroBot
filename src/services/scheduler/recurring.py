"""Job: spawn next occurrence for recurring meetings."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.keyboards.meeting import vote_keyboard
from src.database.models.meeting import RecurrenceRule
from src.database.models.user import User
from src.database.repositories.meeting import MeetingRepository
from src.services.meeting_card import build_card

logger = logging.getLogger(__name__)


def next_occurrence(dt: datetime, rule: str) -> datetime:
    """Calculate the next occurrence datetime based on recurrence rule."""
    if rule == RecurrenceRule.WEEKLY.value:
        return dt + timedelta(weeks=1)
    if rule == RecurrenceRule.BIWEEKLY.value:
        return dt + timedelta(weeks=2)
    if rule == RecurrenceRule.MONTHLY.value:
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month = 1
            year += 1
        day = min(dt.day, 28)  # safe for all months
        return dt.replace(year=year, month=month, day=day)
    return dt


async def spawn_recurring_meetings(bot: Bot, sf: async_sessionmaker):
    """
    For each confirmed/completed recurring meeting, create the next occurrence
    if it doesn't already exist and the current occurrence's datetime has passed.
    """
    try:
        async with sf() as session:
            repo = MeetingRepository(session)
            meetings = await repo.get_recurring_needing_spawn()
            now = datetime.now()

            for meeting in meetings:
                if not meeting.proposed_datetime:
                    continue
                if meeting.proposed_datetime > now:
                    continue

                next_dt = next_occurrence(meeting.proposed_datetime, meeting.recurrence)

                if await repo.child_exists(meeting.id, next_dt):
                    continue

                # Get creator info
                creator_stmt = select(User).where(User.id == meeting.creator_id)
                creator_result = await session.execute(creator_stmt)
                creator = creator_result.scalar_one_or_none()
                if not creator:
                    continue

                new_meeting = await repo.create(
                    creator_id=meeting.creator_id,
                    title=meeting.title,
                    proposed_datetime=next_dt,
                    location=meeting.location,
                    chat_id=meeting.chat_id,
                    reminder_minutes=meeting.reminder_minutes,
                    recurrence=meeting.recurrence,
                    parent_meeting_id=meeting.id,
                )

                # Post the card in the group chat
                if meeting.chat_id:
                    try:
                        card = build_card(
                            new_meeting, {}, creator_name=creator.full_name
                        )
                        msg = await bot.send_message(
                            chat_id=meeting.chat_id,
                            text=card,
                            reply_markup=vote_keyboard(new_meeting.id),
                        )
                        await repo.update(new_meeting, message_id=msg.message_id)

                        try:
                            await bot.pin_chat_message(
                                chat_id=meeting.chat_id,
                                message_id=msg.message_id,
                                disable_notification=True,
                            )
                        except Exception:
                            pass

                        logger.info(
                            "Spawned recurring meeting #%d → #%d (%s, %s)",
                            meeting.id,
                            new_meeting.id,
                            meeting.recurrence,
                            next_dt.isoformat(),
                        )
                    except Exception:
                        logger.exception(
                            "Failed to post recurring meeting #%d in chat %d",
                            new_meeting.id,
                            meeting.chat_id,
                        )
    except Exception:
        logger.exception("Error in recurring meetings job")
