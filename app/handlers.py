from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply(f"Привет, {message.from_user.full_name}!")
