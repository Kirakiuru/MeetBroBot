from aiogram import Router, html
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Hello, {html.bold(html.quote(message.from_user.full_name))}!",
        parse_mode=ParseMode.HTML
    )
