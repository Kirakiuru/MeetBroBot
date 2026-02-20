"""Background scheduler: meeting reminders, deadline alerts, weekly nudges, cleanup."""

import logging
from datetime import datetime, timedelta, date

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.models.availability import Availability
from src.database.models.chat_member import ChatMember
from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.user import User
from src.database.models.vote import Vote, VoteChoice
from src.utils.text import safe

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot, session_factory: async_sessionmaker) -> AsyncIOScheduler:
    """Create and configure the scheduler with all recurring jobs."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Meeting reminders — check every minute
    scheduler.add_job(
        _check_meeting_reminders,
        "interval",
        minutes=1,
        args=[bot, session_factory],
        id="meeting_reminders",
        replace_existing=True,
    )

    # Deadline reminders — 30 min before deadline
    scheduler.add_job(
        _check_deadline_reminders,
        "interval",
        minutes=1,
        args=[bot, session_factory],
        id="deadline_reminders",
        replace_existing=True,
    )

    # Weekly schedule nudge — check every hour
    scheduler.add_job(
        _check_weekly_nudges,
        "interval",
        hours=1,
        args=[bot, session_factory],
        id="weekly_nudges",
        replace_existing=True,
    )

    # Cleanup old availability — daily at 07:00
    scheduler.add_job(
        _cleanup_old_slots,
        "cron",
        hour=7,
        minute=0,
        args=[session_factory],
        id="cleanup_slots",
        replace_existing=True,
    )

    return scheduler


# ── Meeting reminders ────────────────────────────────

async def _check_meeting_reminders(bot: Bot, sf: async_sessionmaker):
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


# ── Deadline reminders ───────────────────────────────

async def _check_deadline_reminders(bot: Bot, sf: async_sessionmaker):
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

    # Get who voted
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


# ── Weekly schedule nudge ────────────────────────────

async def _check_weekly_nudges(bot: Bot, sf: async_sessionmaker):
    """
    Check if any users should be nudged to fill their schedule.
    Runs every hour, checks user's preferred day + hour.
    """
    try:
        async with sf() as session:
            now = datetime.now()
            today_dow = now.weekday()  # 0=Mon
            current_hour = now.hour

            stmt = (
                select(User)
                .where(
                    User.schedule_remind == True,  # noqa: E712
                    User.schedule_remind_day == today_dow,
                    User.schedule_remind_hour == current_hour,
                )
            )
            result = await session.execute(stmt)
            users = result.scalars().all()

            for user in users:
                # Check if they already have slots for this week
                week_start = now.date()
                week_end = week_start + timedelta(days=7)

                avail_stmt = (
                    select(Availability)
                    .where(
                        Availability.user_id == user.id,
                        Availability.specific_date >= week_start,
                        Availability.specific_date <= week_end,
                    )
                    .limit(1)
                )
                avail_result = await session.execute(avail_stmt)
                has_slots = avail_result.scalar_one_or_none() is not None

                if not has_slots:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=(
                                "📅 <b>Привет! Новая неделя — новые планы.</b>\n\n"
                                "Заполни расписание → /schedule\n"
                                "Так друзья смогут найти удобное время для встречи.\n\n"
                                "<i>Отключить напоминания: /settings</i>"
                            ),
                        )
                    except Exception:
                        logger.debug("Can't DM user %d for weekly nudge", user.telegram_id)

            if users:
                logger.info("Sent weekly nudges to %d users", len(users))
    except Exception:
        logger.exception("Error in weekly nudge job")


# ── Cleanup old slots ────────────────────────────────

async def _cleanup_old_slots(sf: async_sessionmaker):
    """Delete availability slots for past dates (daily at 7am)."""
    try:
        async with sf() as session:
            yesterday = date.today() - timedelta(days=1)

            stmt = delete(Availability).where(
                and_(
                    Availability.specific_date.isnot(None),
                    Availability.specific_date < yesterday,
                )
            )
            result = await session.execute(stmt)
            count = result.rowcount
            await session.commit()

            if count:
                logger.info("Cleaned up %d old availability slots", count)
    except Exception:
        logger.exception("Error in cleanup job")
