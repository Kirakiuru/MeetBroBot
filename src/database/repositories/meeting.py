from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.meeting import Meeting, MeetingStatus


class MeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        creator_id: int,
        title: str,
        description: str | None = None,
        proposed_datetime: datetime | None = None,
        location: str | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        vote_deadline: datetime | None = None,
        reminder_minutes: int | None = None,
        recurrence: str = "none",
        parent_meeting_id: int | None = None,
    ) -> Meeting:
        meeting = Meeting(
            creator_id=creator_id,
            title=title,
            description=description,
            proposed_datetime=proposed_datetime,
            location=location,
            chat_id=chat_id,
            message_id=message_id,
            vote_deadline=vote_deadline,
            reminder_minutes=reminder_minutes,
            recurrence=recurrence,
            parent_meeting_id=parent_meeting_id,
        )
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def get_by_id(self, meeting_id: int) -> Meeting | None:
        stmt = (
            select(Meeting)
            .options(selectinload(Meeting.votes))
            .where(Meeting.id == meeting_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, meeting: Meeting, **kwargs) -> Meeting:
        for key, value in kwargs.items():
            setattr(meeting, key, value)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def get_active_by_chat(self, chat_id: int) -> list[Meeting]:
        stmt = (
            select(Meeting)
            .options(selectinload(Meeting.votes))
            .where(
                Meeting.chat_id == chat_id,
                Meeting.status == MeetingStatus.PROPOSED,
            )
            .order_by(Meeting.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recurring_needing_spawn(self) -> list[Meeting]:
        """Get confirmed/completed recurring meetings whose next occurrence should be created."""
        stmt = (
            select(Meeting)
            .where(
                Meeting.recurrence != "none",
                Meeting.status.in_([MeetingStatus.CONFIRMED, MeetingStatus.COMPLETED]),
                Meeting.proposed_datetime.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def child_exists(self, parent_id: int, proposed_dt: datetime) -> bool:
        """Check if a child meeting already exists for the given parent + datetime."""
        stmt = select(Meeting.id).where(
            Meeting.parent_meeting_id == parent_id,
            Meeting.proposed_datetime == proposed_dt,
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
