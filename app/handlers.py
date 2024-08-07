from aiogram import F, Router # F - магический фильтр
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

# from app.states import Register
# import app.keyboards as kb
# import app.database.requests as rq

# from aiogram_calendar import SimpleCalendar, get_user_locale


# заменяет явное указание диспетчера
# это позволяет избавиться от неправильного импорта диспетчера из maim
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    # Добавляем юзера в БД
    # await rq.set_user(message.from_user.id)
    # await message.answer('Добро пожаловать', reply_markup=kb.main)
    # await message.reply(f"Hello, {hbold(message.from_user.full_name)}! Pick a calendar", reply_markup=kb.start_kb)
    await message.reply(f"Привет, {message.from_user.full_name}!")


# @router.message(F.text == 'Каталог')
# async def catalog(message: Message):
#     await message.answer('Choose item', reply_markup=await kb.categories())


# @router.message(F.text.lower() == 'navigation calendar')
# async def nav_cal_handler(message: Message):
#     await message.answer(
#         "Please select a date: ",
#         reply_markup=await SimpleCalendar(locale=await get_user_locale(message.from_user)).start_calendar()
#     )
