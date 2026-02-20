from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.vote import Vote, VoteChoice


class VoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        meeting_id: int,
        user_id: int,
        choice: VoteChoice,
    ) -> tuple[Vote, bool]:
        """Create or update a vote. Returns (vote, is_changed)."""
        stmt = select(Vote).where(
            Vote.meeting_id == meeting_id,
            Vote.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        vote = result.scalar_one_or_none()

        is_changed = False
        if vote is None:
            vote = Vote(
                meeting_id=meeting_id,
                user_id=user_id,
                choice=choice,
            )
            self.session.add(vote)
        else:
            is_changed = vote.choice != choice
            vote.choice = choice

        await self.session.commit()
        await self.session.refresh(vote)
        return vote, is_changed

    async def get_by_meeting(self, meeting_id: int) -> list[Vote]:
        stmt = select(Vote).where(Vote.meeting_id == meeting_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_vote(self, meeting_id: int, user_id: int) -> Vote | None:
        stmt = select(Vote).where(
            Vote.meeting_id == meeting_id,
            Vote.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
