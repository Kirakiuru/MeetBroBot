"""Tests for repository layer (CRUD operations)."""

import pytest
from datetime import date, time, datetime, timedelta

from src.database.repositories.user import UserRepository
from src.database.repositories.availability import AvailabilityRepository
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.vote import VoteRepository
from src.database.models.meeting import MeetingStatus
from src.database.models.vote import VoteChoice


# ── User ──────────────────────────────────────────────


class TestUserRepository:
    async def test_create_and_get(self, session):
        repo = UserRepository(session)
        user = await repo.create(telegram_id=123456, username="testuser", full_name="Test User")

        assert user.id is not None
        assert user.telegram_id == 123456
        assert user.username == "testuser"

    async def test_get_by_telegram_id(self, session):
        repo = UserRepository(session)
        await repo.create(telegram_id=111, username="a", full_name="A")

        found = await repo.get_by_telegram_id(111)
        assert found is not None
        assert found.full_name == "A"

        missing = await repo.get_by_telegram_id(999)
        assert missing is None

    async def test_get_by_id(self, session):
        repo = UserRepository(session)
        user = await repo.create(telegram_id=222, username="b", full_name="B")

        found = await repo.get_by_id(user.id)
        assert found is not None
        assert found.telegram_id == 222

    async def test_update(self, session):
        repo = UserRepository(session)
        user = await repo.create(telegram_id=333, username="c", full_name="Old")

        updated = await repo.update(user, full_name="New", schedule_remind=False)
        assert updated.full_name == "New"
        assert updated.schedule_remind is False

    async def test_default_reminder_settings(self, session):
        repo = UserRepository(session)
        user = await repo.create(telegram_id=444, username="d", full_name="D")

        assert user.schedule_remind is True
        assert user.schedule_remind_day == 0  # Monday
        assert user.schedule_remind_hour == 12


# ── Availability ──────────────────────────────────────


class TestAvailabilityRepository:
    async def test_add_and_get(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=100, username="u", full_name="U")

        avail_repo = AvailabilityRepository(session)
        slot = await avail_repo.add(
            user_id=user.id,
            day_of_week=None,
            start_time=time(10, 0),
            end_time=time(12, 0),
            is_recurring=False,
            specific_date=date(2026, 2, 25),
        )
        assert slot.id is not None

        slots = await avail_repo.get_by_user(user.id)
        assert len(slots) == 1
        assert slots[0].start_time == time(10, 0)

    async def test_delete_by_id(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=101, username="u1", full_name="U1")

        avail_repo = AvailabilityRepository(session)
        s1 = await avail_repo.add(
            user_id=user.id, day_of_week=None,
            start_time=time(9, 0), end_time=time(11, 0),
            is_recurring=False, specific_date=date(2026, 3, 1),
        )
        s2 = await avail_repo.add(
            user_id=user.id, day_of_week=None,
            start_time=time(14, 0), end_time=time(16, 0),
            is_recurring=False, specific_date=date(2026, 3, 1),
        )

        deleted = await avail_repo.delete_by_id(s1.id, user.id)
        assert deleted is True

        remaining = await avail_repo.get_by_user(user.id)
        assert len(remaining) == 1
        assert remaining[0].id == s2.id

    async def test_delete_by_id_wrong_user(self, session):
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=102, username="u2", full_name="U2")
        u2 = await user_repo.create(telegram_id=103, username="u3", full_name="U3")

        avail_repo = AvailabilityRepository(session)
        slot = await avail_repo.add(
            user_id=u1.id, day_of_week=None,
            start_time=time(9, 0), end_time=time(11, 0),
            is_recurring=False, specific_date=date(2026, 3, 1),
        )

        # u2 tries to delete u1's slot — should fail
        deleted = await avail_repo.delete_by_id(slot.id, u2.id)
        assert deleted is False

    async def test_delete_by_user(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=104, username="u4", full_name="U4")

        avail_repo = AvailabilityRepository(session)
        for h in [9, 12, 15]:
            await avail_repo.add(
                user_id=user.id, day_of_week=None,
                start_time=time(h, 0), end_time=time(h + 2, 0),
                is_recurring=False, specific_date=date(2026, 3, 2),
            )

        count = await avail_repo.delete_by_user(user.id)
        assert count == 3
        assert await avail_repo.get_by_user(user.id) == []


# ── Meeting ───────────────────────────────────────────


class TestMeetingRepository:
    async def test_create_and_get(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=200, username="m", full_name="M")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(
            creator_id=user.id,
            title="Шашлыки",
            proposed_datetime=datetime(2026, 3, 1, 18, 0),
            location="Парк",
            reminder_minutes=60,
        )

        assert meeting.id is not None
        assert meeting.status == MeetingStatus.PROPOSED
        assert meeting.reminder_minutes == 60
        assert meeting.reminder_sent is False

    async def test_update(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=201, username="m1", full_name="M1")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=user.id, title="Бар")

        updated = await meeting_repo.update(
            meeting, status=MeetingStatus.CONFIRMED, message_id=42
        )
        assert updated.status == MeetingStatus.CONFIRMED
        assert updated.message_id == 42

    async def test_get_active_by_chat(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=202, username="m2", full_name="M2")

        meeting_repo = MeetingRepository(session)
        m1 = await meeting_repo.create(
            creator_id=user.id, title="Active", chat_id=-100123
        )
        m2 = await meeting_repo.create(
            creator_id=user.id, title="Also Active", chat_id=-100123
        )
        # Confirmed — should NOT appear
        m3 = await meeting_repo.create(
            creator_id=user.id, title="Done", chat_id=-100123
        )
        await meeting_repo.update(m3, status=MeetingStatus.CONFIRMED)

        active = await meeting_repo.get_active_by_chat(-100123)
        assert len(active) == 2
        titles = {m.title for m in active}
        assert titles == {"Active", "Also Active"}

    async def test_get_active_other_chat(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=203, username="m3", full_name="M3")

        meeting_repo = MeetingRepository(session)
        await meeting_repo.create(creator_id=user.id, title="X", chat_id=-100999)

        result = await meeting_repo.get_active_by_chat(-100111)
        assert len(result) == 0


# ── Vote ──────────────────────────────────────────────


class TestVoteRepository:
    async def test_upsert_new(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=300, username="v", full_name="V")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=user.id, title="Vote Test")

        vote_repo = VoteRepository(session)
        vote, is_changed = await vote_repo.upsert(
            meeting_id=meeting.id, user_id=user.id, choice=VoteChoice.YES
        )

        assert vote.choice == VoteChoice.YES
        assert is_changed is False  # new vote, not a change

    async def test_upsert_change(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=301, username="v1", full_name="V1")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=user.id, title="Re-vote")

        vote_repo = VoteRepository(session)
        await vote_repo.upsert(meeting.id, user.id, VoteChoice.YES)
        vote, is_changed = await vote_repo.upsert(meeting.id, user.id, VoteChoice.NO)

        assert vote.choice == VoteChoice.NO
        assert is_changed is True

    async def test_upsert_same_choice(self, session):
        user_repo = UserRepository(session)
        user = await user_repo.create(telegram_id=302, username="v2", full_name="V2")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=user.id, title="Same")

        vote_repo = VoteRepository(session)
        await vote_repo.upsert(meeting.id, user.id, VoteChoice.MAYBE)
        _, is_changed = await vote_repo.upsert(meeting.id, user.id, VoteChoice.MAYBE)

        assert is_changed is False

    async def test_get_by_meeting(self, session):
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=303, username="v3", full_name="V3")
        u2 = await user_repo.create(telegram_id=304, username="v4", full_name="V4")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=u1.id, title="Multi")

        vote_repo = VoteRepository(session)
        await vote_repo.upsert(meeting.id, u1.id, VoteChoice.YES)
        await vote_repo.upsert(meeting.id, u2.id, VoteChoice.NO)

        votes = await vote_repo.get_by_meeting(meeting.id)
        assert len(votes) == 2
        choices = {v.choice for v in votes}
        assert choices == {VoteChoice.YES, VoteChoice.NO}
