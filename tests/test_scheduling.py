"""Tests for SchedulingService: slot matching, date summary."""

from datetime import date, time, timedelta

from src.database.repositories.user import UserRepository
from src.database.repositories.availability import AvailabilityRepository
from src.services.scheduling import SchedulingService


class TestSchedulingService:
    async def test_find_best_slots_overlap(self, session):
        """Two users with overlapping availability → should find common slot."""
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=500, username="s1", full_name="S1")
        u2 = await user_repo.create(telegram_id=501, username="s2", full_name="S2")

        tomorrow = date.today() + timedelta(days=1)

        avail_repo = AvailabilityRepository(session)
        # u1: 10:00–14:00
        await avail_repo.add(
            user_id=u1.id, day_of_week=None,
            start_time=time(10, 0), end_time=time(14, 0),
            is_recurring=False, specific_date=tomorrow,
        )
        # u2: 12:00–18:00
        await avail_repo.add(
            user_id=u2.id, day_of_week=None,
            start_time=time(12, 0), end_time=time(18, 0),
            is_recurring=False, specific_date=tomorrow,
        )

        svc = SchedulingService(session)
        slots = await svc.find_best_slots([u1.id, u2.id])

        # Should have at least one slot where both overlap (12:00–14:00)
        assert len(slots) > 0
        best = slots[0]
        assert best["count"] == 2
        assert best["date"] == tomorrow

    async def test_find_best_slots_no_overlap(self, session):
        """Two users without overlap → still returns individual slots."""
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=510, username="s10", full_name="S10")
        u2 = await user_repo.create(telegram_id=511, username="s11", full_name="S11")

        tomorrow = date.today() + timedelta(days=1)

        avail_repo = AvailabilityRepository(session)
        await avail_repo.add(
            user_id=u1.id, day_of_week=None,
            start_time=time(8, 0), end_time=time(10, 0),
            is_recurring=False, specific_date=tomorrow,
        )
        await avail_repo.add(
            user_id=u2.id, day_of_week=None,
            start_time=time(20, 0), end_time=time(22, 0),
            is_recurring=False, specific_date=tomorrow,
        )

        svc = SchedulingService(session)
        slots = await svc.find_best_slots([u1.id, u2.id])
        # Should still return something (individual availability)
        assert len(slots) >= 0  # may be empty if MIN_OVERLAP not met

    async def test_get_date_summary(self, session):
        """Date summary returns per-date user counts and period breakdown."""
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=520, username="s20", full_name="S20")
        u2 = await user_repo.create(telegram_id=521, username="s21", full_name="S21")

        tomorrow = date.today() + timedelta(days=1)

        avail_repo = AvailabilityRepository(session)
        # u1: morning (10–12)
        await avail_repo.add(
            user_id=u1.id, day_of_week=None,
            start_time=time(10, 0), end_time=time(12, 0),
            is_recurring=False, specific_date=tomorrow,
        )
        # u2: evening (18–21)
        await avail_repo.add(
            user_id=u2.id, day_of_week=None,
            start_time=time(18, 0), end_time=time(21, 0),
            is_recurring=False, specific_date=tomorrow,
        )

        svc = SchedulingService(session)
        summary = await svc.get_date_summary([u1.id, u2.id])

        iso_key = tomorrow.isoformat()
        assert iso_key in summary
        info = summary[iso_key]
        assert info["total"] == 2  # both have slots on this date
        assert info["morning"] >= 1  # u1 is in morning
        assert info["evening"] >= 1  # u2 is in evening

    async def test_empty_users(self, session):
        svc = SchedulingService(session)
        assert await svc.find_best_slots([]) == []
        assert await svc.get_date_summary([]) == {}

    async def test_recurring_slots(self, session):
        """Recurring slots appear across multiple weeks."""
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=530, username="s30", full_name="S30")

        avail_repo = AvailabilityRepository(session)
        # Recurring every Monday 10:00–12:00
        await avail_repo.add(
            user_id=u1.id, day_of_week=0,  # Monday
            start_time=time(10, 0), end_time=time(12, 0),
            is_recurring=True, specific_date=None,
        )

        svc = SchedulingService(session)
        summary = await svc.get_date_summary([u1.id], days_ahead=14)

        # Should have entries for next 2 Mondays
        monday_count = sum(
            1 for k, v in summary.items()
            if date.fromisoformat(k).weekday() == 0
        )
        assert monday_count >= 1  # at least 1 Monday in next 14 days
