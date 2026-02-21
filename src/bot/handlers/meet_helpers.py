"""Shared guards, parsers, formatters, and step-transition helpers for /meet flow."""

from datetime import datetime

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.meeting import (
    confirm_meeting_keyboard,
    deadline_keyboard,
    location_keyboard,
    recurrence_keyboard,
    reminder_keyboard,
)
from src.bot.states import MeetStates
from src.database.models.user import User
from src.database.repositories.chat_member import ChatMemberRepository
from src.utils.text import safe


# ── Guards ─────────────────────────────────────────────

async def is_owner(callback: CallbackQuery, state: FSMContext) -> bool:
    """Block other users from clicking mid-creation buttons."""
    current = await state.get_state()
    if not current:
        await callback.answer(
            "⛔ Это не твоя сессия — запусти /meet сам",
            show_alert=True,
        )
        return False
    return True


# ── Parsers ────────────────────────────────────────────

def parse_state_datetime(data: dict) -> datetime | None:
    raw = data.get("proposed_datetime")
    if not raw:
        return None
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return raw


def parse_deadline(data: dict) -> datetime | None:
    raw = data.get("vote_deadline")
    if not raw:
        return None
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return raw


# ── Formatters ─────────────────────────────────────────

def format_meeting_preview(data: dict) -> str:
    title = data.get("title", "—")
    lines = [f"🎯 <b>{safe(title)}</b>"]
    dt = parse_state_datetime(data)
    if dt:
        lines.append(f"📅 {dt.strftime('%d.%m.%Y %H:%M')}")
    if data.get("location"):
        lines.append(f"📍 {safe(data['location'])}")
    dl = parse_deadline(data)
    if dl:
        lines.append(f"⏰ Дедлайн: {dl.strftime('%d.%m %H:%M')}")
    rem = data.get("reminder_minutes")
    if rem:
        label = f"{rem // 60} ч" if rem >= 60 else f"{rem} мин"
        lines.append(f"🔔 Напоминание: за {label}")
    rec = data.get("recurrence", "none")
    if rec and rec != "none":
        rec_labels = {
            "weekly": "Каждую неделю",
            "biweekly": "Раз в 2 недели",
            "monthly": "Раз в месяц",
        }
        lines.append(f"🔁 {rec_labels.get(rec, rec)}")
    return "\n".join(lines)


# ── Utilities ──────────────────────────────────────────

def is_group_chat(msg: Message) -> bool:
    return msg.chat.type in ("group", "supergroup")


async def get_user_ids(msg: Message, session: AsyncSession) -> list[int]:
    if is_group_chat(msg):
        cm_repo = ChatMemberRepository(session)
        return await cm_repo.get_user_ids_in_chat(msg.chat.id)
    stmt = select(User.id)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── Step transition helpers ────────────────────────────

async def go_to_location(msg: Message, state: FSMContext):
    await state.set_state(MeetStates.entering_location)
    await msg.answer("📍 <b>Где встречаемся?</b>", reply_markup=location_keyboard())


async def go_to_deadline(msg: Message, state: FSMContext, edit: bool = False):
    await state.set_state(MeetStates.entering_deadline)
    text = "⏰ <b>Дедлайн голосования</b>\n\nДо какого времени нужно проголосовать?"
    if edit:
        await msg.edit_text(text, reply_markup=deadline_keyboard())
    else:
        await msg.answer(text, reply_markup=deadline_keyboard())


async def go_to_reminder(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("proposed_datetime"):
        await state.set_state(MeetStates.entering_reminder)
        await msg.answer(
            "🔔 <b>Напоминание перед встречей?</b>",
            reply_markup=reminder_keyboard(),
        )
    else:
        await state.update_data(reminder_minutes=None)
        await go_to_recurrence(msg, state)


async def go_to_recurrence(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("proposed_datetime"):
        await state.set_state(MeetStates.entering_recurrence)
        await msg.answer(
            "🔁 <b>Повторять встречу?</b>",
            reply_markup=recurrence_keyboard(),
        )
    else:
        await state.update_data(recurrence="none")
        await show_confirm(msg, state)


async def show_confirm(msg: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(MeetStates.confirm)
    preview = format_meeting_preview(data)
    await msg.answer(
        f"{preview}\n\nВсё верно? Создаём?",
        reply_markup=confirm_meeting_keyboard(),
    )
