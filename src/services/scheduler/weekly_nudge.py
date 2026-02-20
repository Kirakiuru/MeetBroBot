"""Job: nudge users to fill weekly schedule."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.database.models.availability import Availability
from src.database.models.user import User

logger = logging.getLogger(__name__)


async def check_weekly_nudges(bot: Bot, sf: async_sessionmaker):
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
                        logger.debug(
                            "Can't DM user %d for weekly nudge", user.telegram_id
                        )

            if users:
                logger.info("Sent weekly nudges to %d users", len(users))
    except Exception:
        logger.exception("Error in weekly nudge job")
