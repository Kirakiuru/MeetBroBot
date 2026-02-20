"""Tests for scheduler background jobs (cleanup, reminder logic)."""

from datetime import date, time, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.models.availability import Availability
from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.vote import Vote, VoteChoice
from src.database.repositories.user import UserRepository
from src.database.repositories.availability import AvailabilityRepository
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.vote import VoteRepository
from src.services.scheduler import _cleanup_old_slots, _check_meeting_reminders


class TestCleanupOldSlots:
    async def test_deletes_past_slots(self, engine, session):
        """Old specific-date slots are deleted, future ones kept."""
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=600, username="cl", full_name="CL")

        avail_repo = AvailabilityRepository(session)
        # Past slot (should be deleted)
        await avail_repo.add(
            user_id=user.id, day_of_week=None,
            start_time=time(10, 0), end_time=time(12, 0),
            is_recurring=False, specific_date=date(2025, 1, 1),
        )
        # Future slot (should remain)
        await avail_repo.add(
            user_id=user.id, day_of_week=None,
            start_time=time(14, 0), end_time=time(16, 0),
            is_recurring=False, specific_date=date(2027, 12, 31),
        )
        # Recurring slot (no specific_date → should remain)
        await avail_repo.add(
            user_id=user.id, day_of_week=1,
            start_time=time(18, 0), end_time=time(20, 0),
            is_recurring=True, specific_date=None,
        )

        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        await _cleanup_old_slots(sf)

        # Re-fetch
        remaining = await avail_repo.get_by_user(user.id)
        assert len(remaining) == 2
        dates = [s.specific_date for s in remaining]
        assert date(2025, 1, 1) not in dates


class TestMeetingReminders:
    async def test_sends_reminder_when_due(self, engine, session):
        """Reminder sent when current time >= proposed_datetime - reminder_minutes."""
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=700, username="rm", full_name="RM")

        meeting_repo = MeetingRepository(session)
        # Meeting in 30 min, reminder set to 60 min → should trigger
        meeting = await meeting_repo.create(
            creator_id=user.id,
            title="Soon",
            proposed_datetime=datetime.now() + timedelta(minutes=30),
            reminder_minutes=60,
            chat_id=-100555,
        )

        # Vote YES
        vote_repo = VoteRepository(session)
        await vote_repo.upsert(meeting.id, user.id, VoteChoice.YES)

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        await _check_meeting_reminders(bot, sf)

        # Bot should have sent DM + group message
        assert bot.send_message.call_count >= 1

        # Check reminder_sent flag
        async with sf() as s2:
            stmt = select(Meeting).where(Meeting.id == meeting.id)
            result = await s2.execute(stmt)
            m = result.scalar_one()
            assert m.reminder_sent is True

    async def test_no_reminder_when_not_due(self, engine, session):
        """Reminder NOT sent when time hasn't come yet."""
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=701, username="rm1", full_name="RM1")

        meeting_repo = MeetingRepository(session)
        # Meeting in 3 hours, reminder 60 min → not yet
        meeting = await meeting_repo.create(
            creator_id=user.id,
            title="Later",
            proposed_datetime=datetime.now() + timedelta(hours=3),
            reminder_minutes=60,
        )

        bot = AsyncMock()
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        await _check_meeting_reminders(bot, sf)

        bot.send_message.assert_not_called()

    async def test_no_double_send(self, engine, session):
        """Already-sent reminders are not sent again."""
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=702, username="rm2", full_name="RM2")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(
            creator_id=user.id,
            title="Done",
            proposed_datetime=datetime.now() + timedelta(minutes=10),
            reminder_minutes=60,
        )
        # Mark as already sent
        await meeting_repo.update(meeting, reminder_sent=True)

        bot = AsyncMock()
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        await _check_meeting_reminders(bot, sf)

        bot.send_message.assert_not_called()
