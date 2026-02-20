"""Handler for /app command — opens the Telegram Mini App."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from src.core.config import settings

router = Router()


@router.message(Command("app"))
async def cmd_app(message: Message):
    if not settings.webapp_url:
        await message.answer(
            "🔧 Mini App пока не настроен.\n"
            "Администратору нужно задать <code>WEBAPP_URL</code> в .env."
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть MeetBro",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )

    await message.answer(
        "📱 <b>MeetBro Mini App</b>\n\n"
        "📅 Визуальный календарь расписания\n"
        "🎯 Все встречи и голосование\n"
        "⚙️ Настройки напоминаний\n\n"
        "Нажми кнопку ниже:",
        reply_markup=kb,
    )
