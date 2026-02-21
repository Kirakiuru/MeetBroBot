from datetime import date, time, timedelta
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.availability import Availability
from src.database.models.user import User

# Minimum people to consider a slot "good"
MIN_OVERLAP = 2


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _minutes_to_time(m: int) -> time:
    return time(m // 60, m % 60)


class SchedulingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_best_slots(
        self,
        user_ids: list[int],
        days_ahead: int = 14,
    ) -> list[dict]:
        """
        Find overlapping availability across users for the next N days.
        Returns list of {date, start, end, count, names} sorted by count desc.
        """
        if not user_ids:
            return []

        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        # Fetch all availability for these users
        stmt = (
            select(Availability, User)
            .join(User, Availability.user_id == User.id)
            .where(Availability.user_id.in_(user_ids))
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Build per-date slots: {date -> [(start_min, end_min, user_name)]}
        date_slots: dict[date, list[tuple[int, int, str]]] = {}

        for avail, user in rows:
            dates_to_check = []

            if avail.specific_date and today <= avail.specific_date <= end_date:
                dates_to_check.append(avail.specific_date)
            elif avail.is_recurring and avail.day_of_week is not None:
                # Expand recurring to actual dates
                d = today
                while d <= end_date:
                    if d.weekday() == avail.day_of_week:
                        dates_to_check.append(d)
                    d += timedelta(days=1)

            start_min = _time_to_minutes(avail.start_time)
            end_min = _time_to_minutes(avail.end_time)

            for dt in dates_to_check:
                date_slots.setdefault(dt, []).append(
                    (start_min, end_min, user.full_name)
                )

        # Find overlaps per date
        suggestions = []

        for dt in sorted(date_slots):
            slots = date_slots[dt]
            if len(slots) < MIN_OVERLAP:
                continue

            # Find time ranges where 2+ people overlap
            overlaps = self._find_overlaps(slots)
            for start_min, end_min, names in overlaps:
                if len(names) >= MIN_OVERLAP:
                    suggestions.append({
                        "date": dt,
                        "start": _minutes_to_time(start_min),
                        "end": _minutes_to_time(end_min),
                        "count": len(names),
                        "names": names,
                    })

        # Sort: most people first, then earliest date
        suggestions.sort(key=lambda s: (-s["count"], s["date"]))
        return suggestions[:10]  # top 10

    # Time preset ranges in minutes
    PRESET_RANGES = {
        "morning": (540, 720),    # 9–12
        "day": (720, 1020),       # 12–17
        "evening": (1020, 1260),  # 17–21
        "night": (1260, 1440),    # 21–00
    }

    async def get_date_summary(
        self,
        user_ids: list[int],
        days_ahead: int = 28,
    ) -> dict[str, dict]:
        """
        Per-date availability with per-period breakdown.
        Returns {iso_date: {"total": N, "morning": N, "day": N, "evening": N, "night": N}}
        """
        if not user_ids:
            return {}

        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        stmt = (
            select(Availability)
            .where(Availability.user_id.in_(user_ids))
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # date -> {user_id -> [(start_min, end_min)]}
        date_user_slots: dict[date, dict[int, list[tuple[int, int]]]] = {}

        for avail in rows:
            dates_to_check: list[date] = []

            if avail.specific_date and today <= avail.specific_date <= end_date:
                dates_to_check.append(avail.specific_date)
            elif avail.is_recurring and avail.day_of_week is not None:
                d = today
                while d <= end_date:
                    if d.weekday() == avail.day_of_week:
                        dates_to_check.append(d)
                    d += timedelta(days=1)

            s = _time_to_minutes(avail.start_time)
            e = _time_to_minutes(avail.end_time)

            for dt in dates_to_check:
                date_user_slots.setdefault(dt, {}).setdefault(avail.user_id, []).append((s, e))

        summary: dict[str, dict] = {}
        for dt, user_slots in date_user_slots.items():
            total = len(user_slots)
            period_counts: dict[str, int] = {}
            for period, (ps, pe) in self.PRESET_RANGES.items():
                count = 0
                for uid, slots in user_slots.items():
                    for s, e in slots:
                        if s < pe and e > ps:  # overlap check
                            count += 1
                            break
                period_counts[period] = count

            summary[dt.isoformat()] = {"total": total, **period_counts}

        return summary

    @staticmethod
    def _find_overlaps(
        slots: list[tuple[int, int, str]],
    ) -> list[tuple[int, int, list[str]]]:
        """
        Given [(start_min, end_min, name), ...],
        find all maximal time ranges where 2+ people overlap.
        """
        # Event-based sweep line
        events: list[tuple[int, int, str]] = []  # (minute, +1/-1, name)
        for s, e, name in slots:
            events.append((s, 1, name))
            events.append((e, -1, name))

        events.sort(key=lambda x: (x[0], x[1]))

        active: Counter = Counter()
        results: list[tuple[int, int, list[str]]] = []
        current_start = None

        for minute, delta, name in events:
            # If we're tracking an overlap and the time advances
            if current_start is not None and minute > current_start and len(active) >= MIN_OVERLAP:
                results.append((current_start, minute, sorted(active.keys())))

            if delta == 1:
                active[name] += 1
            else:
                active[name] -= 1
                if active[name] == 0:
                    del active[name]

            if len(active) >= MIN_OVERLAP:
                current_start = minute
            else:
                current_start = None

        # Merge adjacent segments with same people
        merged = []
        for start, end, names in results:
            if merged and merged[-1][2] == names and merged[-1][1] == start:
                merged[-1] = (merged[-1][0], end, names)
            else:
                merged.append((start, end, names))

        return merged
