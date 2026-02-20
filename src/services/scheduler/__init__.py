"""Background scheduler: orchestrates all recurring jobs."""

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.services.scheduler.auto_suggest import auto_suggest_meetings
from src.services.scheduler.cleanup import cleanup_old_slots
from src.services.scheduler.deadlines import check_deadline_reminders
from src.services.scheduler.recurring import spawn_recurring_meetings
from src.services.scheduler.reminders import check_meeting_reminders
from src.services.scheduler.weekly_nudge import check_weekly_nudges

# Re-export for backwards compat (tests, etc.)
_cleanup_old_slots = cleanup_old_slots
_check_meeting_reminders = check_meeting_reminders


def setup_scheduler(bot: Bot, session_factory: async_sessionmaker) -> AsyncIOScheduler:
    """Create and configure the scheduler with all recurring jobs."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Meeting reminders — check every minute
    scheduler.add_job(
        check_meeting_reminders,
        "interval",
        minutes=1,
        args=[bot, session_factory],
        id="meeting_reminders",
        replace_existing=True,
    )

    # Deadline reminders — 30 min before deadline
    scheduler.add_job(
        check_deadline_reminders,
        "interval",
        minutes=1,
        args=[bot, session_factory],
        id="deadline_reminders",
        replace_existing=True,
    )

    # Weekly schedule nudge — check every hour
    scheduler.add_job(
        check_weekly_nudges,
        "interval",
        hours=1,
        args=[bot, session_factory],
        id="weekly_nudges",
        replace_existing=True,
    )

    # Cleanup old availability — daily at 07:00
    scheduler.add_job(
        cleanup_old_slots,
        "cron",
        hour=7,
        minute=0,
        args=[session_factory],
        id="cleanup_slots",
        replace_existing=True,
    )

    # Recurring meetings — spawn next occurrence (check every hour)
    scheduler.add_job(
        spawn_recurring_meetings,
        "interval",
        hours=1,
        args=[bot, session_factory],
        id="recurring_meetings",
        replace_existing=True,
    )

    # Auto-suggest meetings — daily at 10:00
    scheduler.add_job(
        auto_suggest_meetings,
        "cron",
        hour=10,
        minute=0,
        args=[bot, session_factory],
        id="auto_suggest",
        replace_existing=True,
    )

    return scheduler
