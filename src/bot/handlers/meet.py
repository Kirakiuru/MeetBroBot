"""Meeting creation flow: /meet → title → datetime → location → options → preview."""

from datetime import datetime, date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ForceReply
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.meet_helpers import (
    go_to_deadline,
    go_to_location,
    go_to_recurrence,
    go_to_reminder,
    get_user_ids,
    is_owner,
    show_confirm,
)
from src.bot.keyboards.meeting import (
    date_pick_keyboard,
    slot_pick_keyboard,
    time_pick_keyboard,
    title_presets_keyboard,
)
from src.bot.states import MeetStates
from src.services.scheduling import SchedulingService

router = Router()


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
    if not await is_owner(callback, state):
        return
    title = callback.data.split(":", 1)[1]
    await state.update_data(title=title)
    await _go_to_datetime(callback.message, state, session, edit=True)
    await callback.answer()


# ── Custom title ───────────────────────────────────────

@router.callback_query(F.data == "meet_title_custom")
async def on_title_custom(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
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


# ── Helper: go to datetime step ───────────────────────

async def _go_to_datetime(
    msg: Message,
    state: FSMContext,
    session: AsyncSession,
    edit: bool = False,
):
    scheduling = SchedulingService(session)
    user_ids = await get_user_ids(msg, session)

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
    if not await is_owner(callback, state):
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
    await go_to_location(callback.message, state)
    await callback.answer()


# ── Calendar week navigation ───────────────────────────

@router.callback_query(F.data.startswith("meet_pick_date:"))
async def on_pick_date(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
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
    if not await is_owner(callback, state):
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
    if not await is_owner(callback, state):
        return

    parts = callback.data.split(":", 2)
    date_str = parts[1]
    time_str = parts[2]
    dt = datetime.fromisoformat(f"{date_str}T{time_str}")

    await state.update_data(proposed_datetime=dt.isoformat())

    await callback.message.edit_text(f"✅ <b>{dt.strftime('%d.%m %H:%M')}</b>")
    await go_to_location(callback.message, state)
    await callback.answer()


# ── Skip datetime ─────────────────────────────────────

@router.callback_query(F.data == "meet_skip:datetime")
async def on_skip_datetime(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
        return

    await state.update_data(proposed_datetime=None)
    await callback.message.edit_text("⏭ <i>Без даты</i>")
    await go_to_location(callback.message, state)
    await callback.answer()


# ── Location: write address via ForceReply ─────────────

@router.callback_query(F.data == "meet_loc_text")
async def on_loc_text(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
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
    if not await is_owner(callback, state):
        return
    await state.update_data(location="🌐 Онлайн")
    await go_to_deadline(callback.message, state, edit=True)
    await callback.answer()


# ── Location: decide later ─────────────────────────────

@router.callback_query(F.data == "meet_loc:later")
async def on_loc_later(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
        return
    await state.update_data(location=None)
    await go_to_deadline(callback.message, state, edit=True)
    await callback.answer()


# ── Location: text typed (address) ─────────────────────

@router.message(MeetStates.entering_location, F.text)
async def on_location_text(message: Message, state: FSMContext):
    await state.update_data(location=message.text.strip())
    await go_to_deadline(message, state, edit=False)


# ── Deadline picked ───────────────────────────────────

@router.callback_query(F.data.startswith("meet_dl:"))
async def on_deadline_picked(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
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

    await go_to_reminder(callback.message, state)
    await callback.answer()


# ── Reminder picked ──────────────────────────────────

@router.callback_query(F.data.startswith("meet_rem:"))
async def on_reminder_picked(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
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

    await go_to_recurrence(callback.message, state)
    await callback.answer()


# ── Recurrence picked ────────────────────────────────

@router.callback_query(F.data.startswith("meet_rec:"))
async def on_recurrence_picked(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback, state):
        return

    choice = callback.data.split(":")[1]
    rec_labels = {
        "weekly": "Каждую неделю",
        "biweekly": "Раз в 2 недели",
        "monthly": "Раз в месяц",
    }

    await state.update_data(recurrence=choice)

    if choice == "none":
        await callback.message.edit_text("🔁 <i>Без повторения</i>")
    else:
        await callback.message.edit_text(f"🔁 <b>{rec_labels.get(choice, choice)}</b>")

    await show_confirm(callback.message, state)
    await callback.answer()


# ── Cancel creation ────────────────────────────────────

@router.callback_query(F.data == "meet_cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Встреча отменена.")
    await callback.answer()
