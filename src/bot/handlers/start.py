from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.services.user import UserService
from src.utils.text import safe

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    service = UserService(session)
    user, is_new = await service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    name = safe(message.from_user.full_name)

    # Build keyboard with WebApp button if configured
    kb = None
    if settings.webapp_url:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 Открыть Mini App",
                        web_app=WebAppInfo(url=settings.webapp_url),
                    )
                ]
            ]
        )

    if is_new:
        await message.answer(
            f"👋 Привет, <b>{name}</b>!\n\n"
            f"Я <b>MeetBro</b> — помогу организовать встречу с друзьями.\n\n"
            f"<b>Начни здесь:</b>\n"
            f"📅 /schedule — заполни своё расписание\n"
            f"📱 /app — визуальный календарь\n\n"
            f"<b>Потом:</b>\n"
            f"Добавь меня в групповой чат → /meet создаст встречу, "
            f"и я подберу время, когда все свободны.\n\n"
            f"ℹ️ /help — подробная справка",
            reply_markup=kb,
        )
    else:
        await message.answer(
            f"С возвращением, <b>{name}</b>! 🤙\n\n"
            f"📅 /schedule — обновить расписание\n"
            f"📱 /app — визуальный календарь\n"
            f"ℹ️ /help — справка",
            reply_markup=kb,
        )
