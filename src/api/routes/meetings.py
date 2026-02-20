"""Meetings API: list meetings, vote."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_db, get_current_user
from src.database.models.chat_member import ChatMember
from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.user import User
from src.database.models.vote import VoteChoice
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.vote import VoteRepository
from src.services.meeting_card import get_votes_grouped
from src.utils.text import safe

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingOut(BaseModel):
    id: int
    title: str
    status: str
    proposed_datetime: str | None
    location: str | None
    creator_name: str
    vote_deadline: str | None
    votes: dict[str, list[str]]  # {"yes": ["Alice"], "no": [...], ...}
    my_vote: str | None


class VoteIn(BaseModel):
    choice: str  # yes / no / maybe


@router.get("", response_model=list[MeetingOut])
async def get_my_meetings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get all active meetings from user's groups."""
    # Find user's group chats
    cm_stmt = select(ChatMember.chat_id).where(ChatMember.user_id == user.id)
    cm_result = await session.execute(cm_stmt)
    chat_ids = [row[0] for row in cm_result.all()]

    if not chat_ids:
        return []

    # Get proposed meetings from those chats
    stmt = (
        select(Meeting)
        .where(
            Meeting.chat_id.in_(chat_ids),
            Meeting.status == MeetingStatus.PROPOSED,
        )
        .order_by(Meeting.created_at.desc())
    )
    result = await session.execute(stmt)
    meetings = result.scalars().all()

    out = []
    for m in meetings:
        # Creator name
        creator_stmt = select(User).where(User.id == m.creator_id)
        creator_result = await session.execute(creator_stmt)
        creator = creator_result.scalar_one_or_none()

        # Votes
        votes_grouped = await get_votes_grouped(session, m.id)

        # My vote
        vote_repo = VoteRepository(session)
        my_vote_obj = await vote_repo.get_user_vote(m.id, user.id)

        out.append(MeetingOut(
            id=m.id,
            title=m.title,
            status=m.status.value,
            proposed_datetime=m.proposed_datetime.isoformat() if m.proposed_datetime else None,
            location=m.location,
            creator_name=creator.full_name if creator else "?",
            vote_deadline=m.vote_deadline.isoformat() if m.vote_deadline else None,
            votes=votes_grouped,
            my_vote=my_vote_obj.choice.value if my_vote_obj else None,
        ))

    return out


@router.post("/{meeting_id}/vote")
async def vote(
    meeting_id: int,
    body: VoteIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    choice_map = {"yes": VoteChoice.YES, "no": VoteChoice.NO, "maybe": VoteChoice.MAYBE}
    choice = choice_map.get(body.choice)
    if not choice:
        raise HTTPException(400, "Invalid choice")

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if not meeting or meeting.status != MeetingStatus.PROPOSED:
        raise HTTPException(404, "Meeting not found or closed")

    vote_repo = VoteRepository(session)
    vote_obj, is_changed = await vote_repo.upsert(meeting.id, user.id, choice)

    return {"ok": True, "choice": vote_obj.choice.value, "changed": is_changed}
