"""User settings API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_db, get_current_user
from src.database.models.user import User
from src.database.repositories.user import UserRepository

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    schedule_remind: bool
    schedule_remind_day: int
    schedule_remind_hour: int


class SettingsUpdate(BaseModel):
    schedule_remind: bool | None = None
    schedule_remind_day: int | None = None
    schedule_remind_hour: int | None = None


@router.get("", response_model=SettingsOut)
async def get_settings(user: User = Depends(get_current_user)):
    return SettingsOut(
        schedule_remind=user.schedule_remind,
        schedule_remind_day=user.schedule_remind_day,
        schedule_remind_hour=user.schedule_remind_hour,
    )


@router.put("", response_model=SettingsOut)
async def update_settings(
    body: SettingsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    repo = UserRepository(session)
    update_data = body.model_dump(exclude_none=True)
    if update_data:
        await repo.update(user, **update_data)
    return SettingsOut(
        schedule_remind=user.schedule_remind,
        schedule_remind_day=user.schedule_remind_day,
        schedule_remind_hour=user.schedule_remind_hour,
    )
