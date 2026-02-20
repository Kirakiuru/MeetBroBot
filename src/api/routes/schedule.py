"""Schedule API: CRUD for availability slots."""

from datetime import date, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_db, get_current_user
from src.database.models.user import User
from src.database.repositories.availability import AvailabilityRepository

router = APIRouter(prefix="/schedule", tags=["schedule"])


class SlotOut(BaseModel):
    id: int
    day_of_week: int | None
    start_time: str  # HH:MM
    end_time: str
    is_recurring: bool
    specific_date: str | None  # YYYY-MM-DD


class SlotCreate(BaseModel):
    day_of_week: int | None = None
    start_time: str  # HH:MM
    end_time: str
    is_recurring: bool = False
    specific_date: str | None = None  # YYYY-MM-DD


def _slot_to_out(s) -> SlotOut:
    return SlotOut(
        id=s.id,
        day_of_week=s.day_of_week,
        start_time=s.start_time.strftime("%H:%M"),
        end_time=s.end_time.strftime("%H:%M"),
        is_recurring=s.is_recurring,
        specific_date=s.specific_date.isoformat() if s.specific_date else None,
    )


@router.get("", response_model=list[SlotOut])
async def get_slots(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    repo = AvailabilityRepository(session)
    slots = await repo.get_by_user(user.id)
    return [_slot_to_out(s) for s in slots]


@router.post("", response_model=SlotOut, status_code=201)
async def create_slot(
    body: SlotCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    repo = AvailabilityRepository(session)

    h_start, m_start = map(int, body.start_time.split(":"))
    h_end, m_end = map(int, body.end_time.split(":"))

    slot = await repo.add(
        user_id=user.id,
        day_of_week=body.day_of_week,
        start_time=time(h_start, m_start),
        end_time=time(h_end, m_end),
        is_recurring=body.is_recurring,
        specific_date=date.fromisoformat(body.specific_date) if body.specific_date else None,
    )
    return _slot_to_out(slot)


@router.delete("/{slot_id}")
async def delete_slot(
    slot_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    repo = AvailabilityRepository(session)
    deleted = await repo.delete_by_id(slot_id, user.id)
    if not deleted:
        return {"ok": False, "detail": "Not found"}
    return {"ok": True}


@router.delete("")
async def clear_all(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    repo = AvailabilityRepository(session)
    count = await repo.delete_by_user(user.id)
    return {"ok": True, "deleted": count}
