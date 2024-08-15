from datetime import datetime

from aiogram import Router, html, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.enums import ParseMode
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, DialogCalendar, DialogCalendarCallback, \
    get_user_locale

import app.keyboards as kb


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {html.bold(html.quote(message.from_user.full_name))}💫" +
        "\nВыбери дату /calendar 📆",
        parse_mode=ParseMode.HTML
    )


@router.message(Command('calendar'))
async def cmd_calendar(message: Message):
    await message.answer('Выбери тип календаря', reply_markup=kb.calendar_type)


@router.message(F.text.lower() == 'navigation calendar')
async def nav_cal_handler(message: Message):
    await message.answer(
        "Please select a date: ",
        reply_markup=await SimpleCalendar(locale=await get_user_locale(message.from_user)).start_calendar()
    )


@router.message(F.text.lower() == 'navigation calendar w month')
async def nav_cal_handler_date(message: Message):
    calendar = SimpleCalendar(
        locale=await get_user_locale(message.from_user), show_alerts=True
    )
    calendar.set_dates_range(datetime(2022, 1, 1), datetime(2025, 12, 31))
    await message.answer(
        "Calendar opened on feb 2023. Please select a date: ",
        reply_markup=await calendar.start_calendar(year=2023, month=2)
    )


@router.callback_query(SimpleCalendarCallback.filter())
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: CallbackData):
    calendar = SimpleCalendar(
        locale=await get_user_locale(callback_query.from_user), show_alerts=True
    )
    calendar.set_dates_range(datetime(2022, 1, 1), datetime(2025, 12, 31))
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(
            f'You selected {date.strftime("%d/%m/%Y")} 💩',
            reply_markup=kb.calendar_type
        )


@router.message(F.text.lower() == 'dialog calendar')
async def dialog_cal_handler(message: Message):
    await message.answer(
        "Please select a date: ",
        reply_markup=await DialogCalendar(
            locale=await get_user_locale(message.from_user)
        ).start_calendar()
    )


@router.message(F.text.lower() == 'dialog calendar w year')
async def dialog_cal_handler_year(message: Message):
    await message.answer(
        "Calendar opened years selection around 1989. Please select a date: ",
        reply_markup=await DialogCalendar(
            locale=await get_user_locale(message.from_user)
        ).start_calendar(1989)
    )


@router.message(F.text.lower() == 'dialog calendar w month')
async def dialog_cal_handler_month(message: Message):
    await message.answer(
        "Calendar opened on sep 1989. Please select a date: ",
        reply_markup=await DialogCalendar(
            locale=await get_user_locale(message.from_user)
        ).start_calendar(year=1989, month=9)
    )


@router.callback_query(DialogCalendarCallback.filter())
async def process_dialog_calendar(callback_query: CallbackQuery, callback_data: CallbackData):
    selected, date = await DialogCalendar(
        locale=await get_user_locale(callback_query.from_user)
    ).process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(
            f'You selected {date.strftime("%d/%m/%Y")}',
            reply_markup=kb.calendar_type
        )
