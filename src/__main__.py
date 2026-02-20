import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from src.core.config import settings
from src.database.engine import async_session
from src.bot.handlers.start import router as start_router
from src.bot.handlers.schedule import router as schedule_router
from src.bot.handlers.meet import router as meet_router
from src.bot.handlers.vote import router as vote_router
from src.bot.handlers.help import router as help_router
from src.bot.handlers.group import router as group_router
from src.bot.middlewares.db import DbSessionMiddleware
from src.bot.middlewares.chat_tracker import ChatTrackerMiddleware
from src.bot.middlewares.throttle import ThrottleMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM storage: Redis if configured, else in-memory
    storage = None
    if settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage.from_url(settings.redis_url)
            logger.info("Using Redis FSM storage")
        except Exception as e:
            logger.warning("Redis unavailable (%s), falling back to MemoryStorage", e)

    dp = Dispatcher(storage=storage)

    # Middlewares (order matters: throttle → DB session → tracker)
    dp.message.middleware(ThrottleMiddleware(rate=5, period=10))
    dp.callback_query.middleware(ThrottleMiddleware(rate=10, period=10))
    dp.update.middleware(DbSessionMiddleware(session_factory=async_session))
    dp.message.middleware(ChatTrackerMiddleware())
    dp.callback_query.middleware(ChatTrackerMiddleware())

    # Routers
    dp.include_router(group_router)  # my_chat_member events
    dp.include_router(start_router)
    dp.include_router(schedule_router)
    dp.include_router(meet_router)
    dp.include_router(vote_router)
    dp.include_router(help_router)

    # Register bot commands menu
    private_commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="schedule", description="📅 Моё расписание"),
        BotCommand(command="meet", description="🎯 Создать встречу"),
        BotCommand(command="help", description="ℹ️ Справка"),
    ]
    group_commands = [
        BotCommand(command="meet", description="🎯 Создать встречу"),
        BotCommand(command="schedule", description="📅 Моё расписание"),
        BotCommand(command="help", description="ℹ️ Справка"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    logger.info("✅ Bot commands registered")

    logger.info("🚀 MeetBroBot starting...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
