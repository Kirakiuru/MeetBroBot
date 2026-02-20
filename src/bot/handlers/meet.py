from datetime import datetime, date, timedelta

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ForceReply
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.meeting import (
    title_presets_keyboard,
    confirm_meeting_keyboard,
    slot_pick_keyboard,
    location_keyboard,
    deadline_keyboard,
    reminder_keyboard,
    vote_keyboard,
    date_pick_keyboard,
    time_pick_keyboard,
)
from src.bot.states import MeetStates
from src.database.models.meeting import MeetingStatus
from src.database.models.user import User
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.user import UserRepository
from src.database.repositories.chat_member import ChatMemberRepository
from src.services.meeting_card import build_card, get_votes_grouped
from src.services.scheduling import SchedulingService
from src.utils.text import safe

router = Router()


# ── Guards ─────────────────────────────────────────────

async def _is_owner(callback: CallbackQuery, state: FSMContext) -> bool:
    """Block other users from clicking mid-creation buttons."""
    current = await state.get_state()
    if not current:
        await callback.answer(
            "⛔ Это не твоя сессия — запусти /meet сам",
            show_alert=True,
        )
        return False
    return True


# ── Helpers ────────────────────────────────────────────

def _parse_state_datetime(data: dict) -> datetime | None:
    raw = data.get("proposed_datetime")
    if not raw:
        return None
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return raw


def _parse_deadline(data: dict) -> datetime | None:
    raw = data.get("vote_deadline")
    if not raw:
        return None
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return raw


def _format_meeting_preview(data: dict) -> str:
    title = data.get("title", "—")
    lines = [f"🎯 <b>{safe(title)}</b>"]
    dt = _parse_state_datetime(data)
    if dt:
        lines.append(f"📅 {dt.strftime('%d.%m.%Y %H:%M')}")
    if data.get("location"):
        lines.append(f"📍 {safe(data['location'])}")
    dl = _parse_deadline(data)
    if dl:
        lines.append(f"⏰ Дедлайн: {dl.strftime('%d.%m %H:%M')}")
    rem = data.get("reminder_minutes")
    if rem:
        label = f"{rem // 60} ч" if rem >= 60 else f"{rem} мин"
        lines.append(f"🔔 Напоминание: за {label}")
    return "\n".join(lines)


def _is_group_chat(msg: Message) -> bool:
    return msg.chat.type in ("group", "supergroup")


# ── /meet ──────────────────────────────────────────────

@router.message(Command("meet"))
async def cmd_meet(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MeetStates.entering_title)
    await message.answer(
        "🎯 <b>Создание встречи</b>\n\n"
        "Выбери тип или введи своё:",
        reply_markup=title_presets_keyboard(),
    )


# ── Title preset picked ───────────────────────────────

@router.callback_query(F.data.startswith("meet_title:"))
async def on_title_preset(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    if not await _is_owner(callback, state):
        return
    title = callback.data.split(":", 1)[1]
    await state.update_data(title=title)
    await _go_to_datetime(callback.message, state, session, edit=True)
    await callback.answer()


# ── Custom title ───────────────────────────────────────

@router.callback_query(F.data == "meet_title_custom")
async def on_title_custom(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return
    await state.set_state(MeetStates.entering_title)
    await callback.message.edit_text("✏️ Введи название встречи:")
    await callback.message.answer(
        "Название:",
        reply_markup=ForceReply(input_field_placeholder="Шашлыки у Паши"),
    )
    await callback.answer()


# ── Title typed (via reply) ────────────────────────────

@router.message(MeetStates.entering_title, F.text)
async def on_title_typed(
    message: Message, state: FSMContext, session: AsyncSession
):
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer(
            "❌ Название 1–200 символов.",
            reply_markup=ForceReply(input_field_placeholder="Название встречи"),
        )
        return
    await state.update_data(title=title)
    await _go_to_datetime(message, state, session, edit=False)


# ── Helper: get relevant user IDs ─────────────────────

async def _get_user_ids(msg: Message, session: AsyncSession) -> list[int]:
    if _is_group_chat(msg):
        cm_repo = ChatMemberRepository(session)
        return await cm_repo.get_user_ids_in_chat(msg.chat.id)
    else:
        stmt = select(User.id)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


# ── Helper: go to datetime step ───────────────────────

async def _go_to_datetime(
    msg: Message,
    state: FSMContext,
    session: AsyncSession,
    edit: bool = False,
):
    scheduling = SchedulingService(session)
    user_ids = await _get_user_ids(msg, session)

    suggestions = await scheduling.find_best_slots(user_ids)
    avail_summary = await scheduling.get_date_summary(user_ids)

    await state.update_data(avail_summary=avail_summary)
    await state.set_state(MeetStates.entering_datetime)

    if suggestions:
        await state.update_data(
            suggestions=[
                {
                    "date": s["date"].isoformat(),
                    "start": s["start"].strftime("%H:%M"),
                    "end": s["end"].strftime("%H:%M"),
                    "count": s["count"],
                    "names": s["names"],
                }
                for s in suggestions
            ]
        )
        text = "🧠 <b>Пересечения расписаний:</b>\n\nВыбери слот или свою дату:"
        kb = slot_pick_keyboard(suggestions)
    else:
        if avail_summary:
            text = (
                "📅 <b>Когда встречаемся?</b>\n"
                "<i>Цифры — сколько людей свободны</i>"
            )
        else:
            text = (
                "📅 <b>Когда встречаемся?</b>\n"
                "<i>Никто ещё не заполнил /schedule</i>"
            )
        kb = date_pick_keyboard(0, avail_summary)

    if edit:
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ── Slot picked from suggestions ──────────────────────

@router.callback_query(F.data.startswith("meet_slot:"))
async def on_slot_pick(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    suggestions = data.get("suggestions", [])

    if idx >= len(suggestions):
        await callback.answer("❌ Слот не найден")
        return

    slot = suggestions[idx]
    dt = datetime.fromisoformat(f"{slot['date']}T{slot['start']}")
    await state.update_data(proposed_datetime=dt.isoformat())

    await callback.message.edit_text(
        f"✅ <b>{dt.strftime('%d.%m %H:%M')}</b> ({slot['count']} свободны)"
    )
    await _go_to_location(callback.message, state)
    await callback.answer()


# ── Calendar week navigation ───────────────────────────

@router.callback_query(F.data.startswith("meet_pick_date:"))
async def on_pick_date(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    offset = int(callback.data.split(":")[1])
    data = await state.get_data()
    avail_summary = data.get("avail_summary", {})

    await state.set_state(MeetStates.entering_datetime)
    await callback.message.edit_text(
        "📅 <b>Выбери дату:</b>\n<i>Цифры — сколько людей свободны</i>",
        reply_markup=date_pick_keyboard(offset, avail_summary),
    )
    await callback.answer()


# ── Date selected → time presets ──────────────────────

@router.callback_query(F.data.startswith("meet_date:"))
async def on_date_selected(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    date_str = callback.data.split(":")[1]
    selected = date.fromisoformat(date_str)
    DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    day_name = DAYS[selected.weekday()]

    data = await state.get_data()
    avail_summary = data.get("avail_summary", {})
    date_info = avail_summary.get(date_str, {})

    await state.update_data(selected_date=date_str)
    await callback.message.edit_text(
        f"🕐 <b>{day_name} {selected.strftime('%d.%m')}</b> — выбери время:",
        reply_markup=time_pick_keyboard(date_str, date_info),
    )
    await callback.answer()


# ── Time preset selected ──────────────────────────────

@router.callback_query(F.data.startswith("meet_time:"))
async def on_time_selected(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    parts = callback.data.split(":", 2)
    date_str = parts[1]
    time_str = parts[2]
    dt = datetime.fromisoformat(f"{date_str}T{time_str}")

    await state.update_data(proposed_datetime=dt.isoformat())

    await callback.message.edit_text(f"✅ <b>{dt.strftime('%d.%m %H:%M')}</b>")
    await _go_to_location(callback.message, state)
    await callback.answer()


# ── Skip datetime ─────────────────────────────────────

@router.callback_query(F.data == "meet_skip:datetime")
async def on_skip_datetime(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    await state.update_data(proposed_datetime=None)
    await callback.message.edit_text("⏭ <i>Без даты</i>")
    await _go_to_location(callback.message, state)
    await callback.answer()


# ── Helper: go to location step ───────────────────────

async def _go_to_location(msg: Message, state: FSMContext):
    await state.set_state(MeetStates.entering_location)
    await msg.answer(
        "📍 <b>Где встречаемся?</b>",
        reply_markup=location_keyboard(),
    )


# ── Location: write address via ForceReply ─────────────

@router.callback_query(F.data == "meet_loc_text")
async def on_loc_text(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return
    await callback.message.edit_text("📍 Жду адрес...")
    await callback.message.answer(
        "Введи адрес или название места:",
        reply_markup=ForceReply(input_field_placeholder="Парк Горького"),
    )
    await callback.answer()


# ── Location: online ───────────────────────────────────

@router.callback_query(F.data == "meet_loc:online")
async def on_loc_online(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return
    await state.update_data(location="🌐 Онлайн")
    await _go_to_deadline(callback.message, state, edit=True)
    await callback.answer()


# ── Location: decide later ─────────────────────────────

@router.callback_query(F.data == "meet_loc:later")
async def on_loc_later(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return
    await state.update_data(location=None)
    await _go_to_deadline(callback.message, state, edit=True)
    await callback.answer()


# ── Location: text typed (address) ─────────────────────

@router.message(MeetStates.entering_location, F.text)
async def on_location_text(message: Message, state: FSMContext):
    await state.update_data(location=message.text.strip())
    await _go_to_deadline(message, state, edit=False)


# ── Helper: go to deadline step ───────────────────────

async def _go_to_deadline(msg: Message, state: FSMContext, edit: bool = False):
    await state.set_state(MeetStates.entering_deadline)
    text = "⏰ <b>Дедлайн голосования</b>\n\nДо какого времени нужно проголосовать?"
    if edit:
        await msg.edit_text(text, reply_markup=deadline_keyboard())
    else:
        await msg.answer(text, reply_markup=deadline_keyboard())


# ── Deadline picked ───────────────────────────────────

@router.callback_query(F.data.startswith("meet_dl:"))
async def on_deadline_picked(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    choice = callback.data.split(":")[1]
    now = datetime.now()

    if choice == "1h":
        dl = now + timedelta(hours=1)
    elif choice == "3h":
        dl = now + timedelta(hours=3)
    elif choice == "tomorrow":
        tomorrow = now + timedelta(days=1)
        dl = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    elif choice == "2d":
        dl = now + timedelta(days=2)
    else:  # none
        dl = None

    if dl:
        await state.update_data(vote_deadline=dl.isoformat())
        await callback.message.edit_text(
            f"⏰ Дедлайн: <b>{dl.strftime('%d.%m %H:%M')}</b>"
        )
    else:
        await state.update_data(vote_deadline=None)
        await callback.message.edit_text("♾ <i>Без дедлайна</i>")

    await _go_to_reminder(callback.message, state)
    await callback.answer()


# ── Helper: go to reminder step (only if datetime set) ─

async def _go_to_reminder(msg: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("proposed_datetime"):
        await state.set_state(MeetStates.entering_reminder)
        await msg.answer(
            "🔔 <b>Напоминание перед встречей?</b>",
            reply_markup=reminder_keyboard(),
        )
    else:
        # No date — skip reminder, go to confirm
        await state.update_data(reminder_minutes=None)
        await _show_confirm(msg, state)


# ── Reminder picked ──────────────────────────────────

@router.callback_query(F.data.startswith("meet_rem:"))
async def on_reminder_picked(callback: CallbackQuery, state: FSMContext):
    if not await _is_owner(callback, state):
        return

    choice = callback.data.split(":")[1]

    if choice == "none":
        await state.update_data(reminder_minutes=None)
        await callback.message.edit_text("🔕 <i>Без напоминания</i>")
    else:
        minutes = int(choice)
        await state.update_data(reminder_minutes=minutes)
        if minutes >= 60:
            label = f"{minutes // 60} ч"
        else:
            label = f"{minutes} мин"
        await callback.message.edit_text(f"🔔 Напомню за <b>{label}</b>")

    await _show_confirm(callback.message, state)
    await callback.answer()


# ── Confirm preview ────────────────────────────────────

async def _show_confirm(
    msg: Message,
    state: FSMContext,
    from_inline: bool = False,
):
    data = await state.get_data()
    await state.set_state(MeetStates.confirm)
    preview = _format_meeting_preview(data)

    # Always send as new message after deadline step
    await msg.answer(
        f"{preview}\n\nВсё верно? Создаём?",
        reply_markup=confirm_meeting_keyboard(),
    )


# ── Cancel creation ────────────────────────────────────

@router.callback_query(F.data == "meet_cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Встреча отменена.")
    await callback.answer()


# ── Confirm → create meeting + vote card ───────────────

@router.callback_query(F.data == "meet_confirm")
async def on_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
):
    if not await _is_owner(callback, state):
        return

    data = await state.get_data()
    await state.clear()

    if "title" not in data:
        await callback.answer(
            "❌ Данные потеряны — начни /meet заново", show_alert=True
        )
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.create(
        creator_id=user.id,
        title=data["title"],
        proposed_datetime=_parse_state_datetime(data),
        location=data.get("location"),
        chat_id=callback.message.chat.id,
        vote_deadline=_parse_deadline(data),
        reminder_minutes=data.get("reminder_minutes"),
    )

    creator_name = user.full_name
    card = build_card(meeting, {}, creator_name=creator_name)
    msg = await callback.message.edit_text(
        card, reply_markup=vote_keyboard(meeting.id)
    )
    await meeting_repo.update(meeting, message_id=msg.message_id)

    # Auto-pin in groups so the card doesn't get buried
    if _is_group_chat(callback.message):
        try:
            await bot.pin_chat_message(
                chat_id=callback.message.chat.id,
                message_id=msg.message_id,
                disable_notification=True,
            )
        except TelegramBadRequest:
            pass  # Bot may lack pin permissions

    await callback.answer("✅ Встреча создана!")


# ── Finalize (creator only) ───────────────────────────

@router.callback_query(F.data.startswith("meet_finalize:"))
async def on_finalize(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    meeting_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if not meeting:
        await callback.answer("❌ Встреча не найдена")
        return
    if meeting.creator_id != user.id:
        await callback.answer(
            "⛔ Только организатор может подтвердить встречу",
            show_alert=True,
        )
        return

    await meeting_repo.update(meeting, status=MeetingStatus.CONFIRMED)

    # Get creator name
    creator = await _get_user_by_id(session, meeting.creator_id)
    creator_name = creator.full_name if creator else ""

    votes = await get_votes_grouped(session, meeting_id)
    card = build_card(meeting, votes, creator_name=creator_name, confirmed=True)
    await callback.message.edit_text(card)

    try:
        await bot.pin_chat_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            disable_notification=False,
        )
    except TelegramBadRequest:
        pass  # Bot may lack pin permissions

    await callback.answer("🎉 Встреча подтверждена!")


# ── Drop (creator only) ───────────────────────────────

@router.callback_query(F.data.startswith("meet_drop:"))
async def on_drop(callback: CallbackQuery, session: AsyncSession):
    meeting_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if not meeting:
        await callback.answer("❌ Встреча не найдена")
        return
    if meeting.creator_id != user.id:
        await callback.answer(
            "⛔ Только организатор может отменить встречу",
            show_alert=True,
        )
        return

    await meeting_repo.update(meeting, status=MeetingStatus.CANCELLED)
    await callback.message.edit_text(
        f"🚫 <b>{safe(meeting.title)}</b> — встреча отменена."
    )
    await callback.answer("Отменена")


# ── Helper ────────────────────────────────────────────

async def _get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
