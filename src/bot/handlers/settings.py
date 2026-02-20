from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.user import UserRepository

router = Router()

DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _settings_keyboard(user) -> InlineKeyboardMarkup:
    status = "✅ Вкл" if user.schedule_remind else "❌ Выкл"
    day = DAYS_RU[user.schedule_remind_day]
    hour = f"{user.schedule_remind_hour:02d}:00"

    rows = [
        [InlineKeyboardButton(
            text=f"Напоминание: {status}",
            callback_data="set_toggle_remind",
        )],
    ]

    if user.schedule_remind:
        rows.append([
            InlineKeyboardButton(text=f"День: {day}", callback_data="set_pick_day"),
            InlineKeyboardButton(text=f"Время: {hour}", callback_data="set_pick_hour"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _day_pick_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, name in enumerate(DAYS_RU):
        row.append(InlineKeyboardButton(text=name, callback_data=f"set_day:{i}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="set_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _hour_pick_keyboard() -> InlineKeyboardMarkup:
    hours = [8, 9, 10, 11, 12, 13, 14, 18, 20]
    rows = []
    row = []
    for h in hours:
        row.append(InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"set_hour:{h}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="set_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала напиши /start")
        return

    status = "✅ включено" if user.schedule_remind else "❌ выключено"
    day = DAYS_RU[user.schedule_remind_day]
    hour = f"{user.schedule_remind_hour:02d}:00"

    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"📅 Напоминание о расписании: <b>{status}</b>\n"
        f"День: <b>{day}</b>, время: <b>{hour}</b>\n\n"
        f"<i>Бот напомнит заполнить расписание на неделю.</i>",
        reply_markup=_settings_keyboard(user),
    )


@router.callback_query(F.data == "set_toggle_remind")
async def on_toggle(callback: CallbackQuery, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    new_val = not user.schedule_remind
    await user_repo.update(user, schedule_remind=new_val)

    status = "✅ включено" if new_val else "❌ выключено"
    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\nНапоминание: <b>{status}</b>",
        reply_markup=_settings_keyboard(user),
    )
    await callback.answer()


@router.callback_query(F.data == "set_pick_day")
async def on_pick_day(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 В какой день напоминать?",
        reply_markup=_day_pick_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_day:"))
async def on_day_selected(callback: CallbackQuery, session: AsyncSession):
    day = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    await user_repo.update(user, schedule_remind_day=day)

    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\nДень: <b>{DAYS_RU[day]}</b> ✅",
        reply_markup=_settings_keyboard(user),
    )
    await callback.answer(f"✅ {DAYS_RU[day]}")


@router.callback_query(F.data == "set_pick_hour")
async def on_pick_hour(callback: CallbackQuery):
    await callback.message.edit_text(
        "🕐 В какое время напоминать?",
        reply_markup=_hour_pick_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_hour:"))
async def on_hour_selected(callback: CallbackQuery, session: AsyncSession):
    hour = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    await user_repo.update(user, schedule_remind_hour=hour)

    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\nВремя: <b>{hour:02d}:00</b> ✅",
        reply_markup=_settings_keyboard(user),
    )
    await callback.answer(f"✅ {hour:02d}:00")


@router.callback_query(F.data == "set_back")
async def on_back(callback: CallbackQuery, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    status = "✅ включено" if user.schedule_remind else "❌ выключено"
    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\nНапоминание: <b>{status}</b>",
        reply_markup=_settings_keyboard(user),
    )
    await callback.answer()
