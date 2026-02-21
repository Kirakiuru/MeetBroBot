import re
from datetime import date, time

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.schedule import (
    DAYS_SHORT,
    week_calendar_keyboard,
    time_presets_keyboard,
)
from src.bot.states import ScheduleStates
from src.database.repositories.availability import AvailabilityRepository
from src.database.repositories.user import UserRepository

router = Router()

TIME_PATTERN = re.compile(
    r"^(\d{1,2})[:\.](\d{2})\s*[-–—]\s*(\d{1,2})[:\.](\d{2})$"
)


def _format_slots(slots) -> str:
    if not slots:
        return "📭 Расписание пустое."

    # Group by date, then by day_of_week (for recurring)
    by_date: dict[date, list] = {}
    by_day: dict[int, list] = {}

    for s in slots:
        if s.specific_date:
            by_date.setdefault(s.specific_date, []).append(s)
        elif s.day_of_week is not None:
            by_day.setdefault(s.day_of_week, []).append(s)

    lines = []

    # Specific dates first (sorted)
    for d in sorted(by_date):
        day_name = DAYS_SHORT[d.weekday()]
        times = ", ".join(
            f"{s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}"
            for s in by_date[d]
        )
        today_mark = " (сегодня)" if d == date.today() else ""
        lines.append(
            f"  <b>{day_name} {d.strftime('%d.%m')}</b>{today_mark}: {times}"
        )

    # Recurring
    for day_idx in sorted(by_day):
        day_name = DAYS_SHORT[day_idx]
        times = ", ".join(
            f"{s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}"
            for s in by_day[day_idx]
        )
        lines.append(f"  <b>{day_name}</b> (каждую): {times}")

    return "📅 <b>Твоё расписание:</b>\n" + "\n".join(lines)


# ── /schedule ──────────────────────────────────────────

@router.message(Command("schedule"))
async def cmd_schedule(message: Message, state: FSMContext):
    await state.set_state(ScheduleStates.choosing_day)
    await state.update_data(week_offset=0)
    await message.answer(
        "📅 <b>Когда ты свободен?</b>\n\n"
        "Выбери дату — я предложу слоты времени:",
        reply_markup=week_calendar_keyboard(0),
    )


# ── Week navigation ───────────────────────────────────

@router.callback_query(F.data.startswith("sched_week:"))
async def on_week_navigate(callback: CallbackQuery, state: FSMContext):
    offset = int(callback.data.split(":")[1])
    await state.update_data(week_offset=offset)
    await callback.message.edit_text(
        "📅 <b>Когда ты свободен?</b>\n\n"
        "Выбери дату:",
        reply_markup=week_calendar_keyboard(offset),
    )
    await callback.answer()


# ── Date selected → show time presets ──────────────────

@router.callback_query(F.data.startswith("sched_date:"))
async def on_date_selected(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]  # YYYY-MM-DD
    selected = date.fromisoformat(date_str)
    day_name = DAYS_SHORT[selected.weekday()]

    await state.update_data(selected_date=date_str)
    await state.set_state(ScheduleStates.choosing_day)  # stay in flow

    await callback.message.edit_text(
        f"🕐 <b>{day_name} {selected.strftime('%d.%m')}</b> — выбери время:",
        reply_markup=time_presets_keyboard(date_str),
    )
    await callback.answer()


# ── Time preset selected ──────────────────────────────

@router.callback_query(F.data.startswith("sched_time:"))
async def on_time_preset(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    # sched_time:2026-02-25:09:00-12:00
    parts = callback.data.split(":", 2)  # ["sched_time", "2026-02-25", "09:00-12:00"]
    date_str = parts[1]
    time_range = parts[2]

    start_str, end_str = time_range.split("-")
    sh, sm = (int(x) for x in start_str.split(":"))
    eh, em = (int(x) for x in end_str.split(":"))
    start = time(sh, sm)
    end = time(eh, em)
    selected = date.fromisoformat(date_str)
    day_name = DAYS_SHORT[selected.weekday()]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    avail_repo = AvailabilityRepository(session)
    await avail_repo.add(
        user_id=user.id,
        day_of_week=selected.weekday(),
        start_time=start,
        end_time=end,
        is_recurring=False,
        specific_date=selected,
    )

    data = await state.get_data()
    week_offset = data.get("week_offset", 0)

    await callback.message.edit_text(
        f"✅ <b>{day_name} {selected.strftime('%d.%m')}</b>: "
        f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}\n\n"
        f"Выбери ещё дату или жми «Готово»:",
        reply_markup=week_calendar_keyboard(week_offset),
    )
    await callback.answer("✅ Добавлено!")


# ── Custom time input ──────────────────────────────────

@router.callback_query(F.data.startswith("sched_custom:"))
async def on_custom_time(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    selected = date.fromisoformat(date_str)
    day_name = DAYS_SHORT[selected.weekday()]

    await state.update_data(selected_date=date_str)
    await state.set_state(ScheduleStates.entering_time)

    await callback.message.edit_text(
        f"⌨️ <b>{day_name} {selected.strftime('%d.%m')}</b> — жду время..."
    )
    await callback.message.answer(
        f"Введи время для <b>{day_name} {selected.strftime('%d.%m')}</b>:\n"
        f"Формат: <code>18:00-22:00</code>",
        reply_markup=ForceReply(input_field_placeholder="18:00-22:00"),
    )
    await callback.answer()


# ── Manual time entry ──────────────────────────────────

@router.message(ScheduleStates.entering_time)
async def on_time_entered(message: Message, state: FSMContext, session: AsyncSession):
    match = TIME_PATTERN.match(message.text.strip())
    if not match:
        await message.answer(
            "❌ Формат: <code>18:00-22:00</code>",
            reply_markup=ForceReply(input_field_placeholder="18:00-22:00"),
        )
        return

    h1, m1, h2, m2 = (int(x) for x in match.groups())
    if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
        await message.answer("❌ Некорректное время.")
        return

    start = time(h1, m1)
    end = time(h2, m2)
    if start >= end:
        await message.answer("❌ Начало должно быть раньше конца.")
        return

    data = await state.get_data()
    date_str = data["selected_date"]
    selected = date.fromisoformat(date_str)
    day_name = DAYS_SHORT[selected.weekday()]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    avail_repo = AvailabilityRepository(session)
    await avail_repo.add(
        user_id=user.id,
        day_of_week=selected.weekday(),
        start_time=start,
        end_time=end,
        is_recurring=False,
        specific_date=selected,
    )

    week_offset = data.get("week_offset", 0)
    await state.set_state(ScheduleStates.choosing_day)

    await message.answer(
        f"✅ <b>{day_name} {selected.strftime('%d.%m')}</b>: "
        f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}\n\n"
        f"Выбери ещё дату или «Готово»:",
        reply_markup=week_calendar_keyboard(week_offset),
    )


# ── Show schedule (with per-slot delete buttons) ──────

@router.callback_query(F.data == "sched_show")
async def on_show_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    avail_repo = AvailabilityRepository(session)
    slots = await avail_repo.get_by_user(user.id)
    text = _format_slots(slots)

    if not slots:
        data = await state.get_data()
        week_offset = data.get("week_offset", 0)
        await callback.message.edit_text(
            text + "\n\nВыбери дату:",
            reply_markup=week_calendar_keyboard(week_offset),
        )
        await callback.answer()
        return

    # Build keyboard with delete buttons per slot
    kb = _edit_schedule_keyboard(slots)
    await callback.message.edit_text(
        text + "\n\n🗑 Нажми чтобы удалить слот:",
        reply_markup=kb,
    )
    await callback.answer()


def _edit_schedule_keyboard(slots) -> InlineKeyboardMarkup:
    """Per-slot delete buttons + back."""
    rows = []
    for s in sorted(slots, key=lambda x: (x.specific_date or date.min, x.start_time)):
        if s.specific_date:
            d = s.specific_date
            day_name = DAYS_SHORT[d.weekday()]
            label = f"🗑 {day_name} {d.strftime('%d.%m')} {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}"
        else:
            day_name = DAYS_SHORT[s.day_of_week] if s.day_of_week is not None else "?"
            label = f"🗑 {day_name} (повтор) {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}"
        rows.append([InlineKeyboardButton(
            text=label, callback_data=f"sched_del:{s.id}"
        )])

    rows.append([
        InlineKeyboardButton(text="🗑 Очистить всё", callback_data="sched_clear"),
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Delete single slot ────────────────────────────────

@router.callback_query(F.data.startswith("sched_del:"))
async def on_delete_slot(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    slot_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    avail_repo = AvailabilityRepository(session)
    deleted = await avail_repo.delete_by_id(slot_id, user.id)

    if deleted:
        await callback.answer("🗑 Слот удалён")
    else:
        await callback.answer("Слот не найден")

    # Refresh the list
    slots = await avail_repo.get_by_user(user.id)
    text = _format_slots(slots)

    if slots:
        kb = _edit_schedule_keyboard(slots)
        await callback.message.edit_text(
            text + "\n\n🗑 Нажми чтобы удалить слот:",
            reply_markup=kb,
        )
    else:
        data = await state.get_data()
        week_offset = data.get("week_offset", 0)
        await callback.message.edit_text(
            "📭 Расписание пусто.\n\nВыбери дату:",
            reply_markup=week_calendar_keyboard(week_offset),
        )


# ── Clear all ──────────────────────────────────────────

@router.callback_query(F.data == "sched_clear")
async def on_clear_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    avail_repo = AvailabilityRepository(session)
    count = await avail_repo.delete_by_user(user.id)

    data = await state.get_data()
    week_offset = data.get("week_offset", 0)

    await callback.message.edit_text(
        f"🗑 Удалено слотов: {count}\n\nВыбери дату:",
        reply_markup=week_calendar_keyboard(week_offset),
    )
    await callback.answer()


# ── Back to calendar ───────────────────────────────────

@router.callback_query(F.data == "sched_back")
async def on_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ScheduleStates.choosing_day)
    data = await state.get_data()
    week_offset = data.get("week_offset", 0)

    await callback.message.edit_text(
        "📅 Выбери дату:",
        reply_markup=week_calendar_keyboard(week_offset),
    )
    await callback.answer()


# ── Noop (disabled buttons) ───────────────────────────

@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery):
    await callback.answer()


# ── Done ───────────────────────────────────────────────

@router.callback_query(F.data == "sched_done")
async def on_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    avail_repo = AvailabilityRepository(session)
    slots = await avail_repo.get_by_user(user.id)
    text = _format_slots(slots)

    await callback.message.edit_text(
        text + "\n\n✅ Сохранено! Создать встречу: /meet"
    )
    await callback.answer()
