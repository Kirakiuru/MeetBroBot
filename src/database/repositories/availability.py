from datetime import date, time

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.availability import Availability


class AvailabilityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        user_id: int,
        day_of_week: int | None,
        start_time: time,
        end_time: time,
        is_recurring: bool = True,
        specific_date: date | None = None,
    ) -> Availability:
        slot = Availability(
            user_id=user_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_recurring=is_recurring,
            specific_date=specific_date,
        )
        self.session.add(slot)
        await self.session.commit()
        await self.session.refresh(slot)
        return slot

    async def get_by_user(self, user_id: int) -> list[Availability]:
        stmt = (
            select(Availability)
            .where(Availability.user_id == user_id)
            .order_by(Availability.day_of_week, Availability.start_time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_user(self, user_id: int) -> int:
        stmt = delete(Availability).where(Availability.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def delete_by_id(self, slot_id: int, user_id: int) -> bool:
        stmt = delete(Availability).where(
            Availability.id == slot_id,
            Availability.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
