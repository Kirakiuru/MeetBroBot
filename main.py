import asyncio
# import logging
from aiogram import Bot, Dispatcher
# from aiogram.enums.parse_mode import ParseMode
# from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers import router
from config import BOT_TOKEN


async def main():
    print('Бот запущен')
    bot = Bot(token=BOT_TOKEN) # parse_mode=ParseMode.HTML
    # обработчик
    dp = Dispatcher() # storage=MemoryStorage()
    # подключаем импортированный роутер из другого файла
    dp.include_router(router)
    # await bot.delete_webhook(drop_pending_updates=True)
    # начинает полинг = опрашивает сервер телеграм
    await dp.start_polling(bot) # allowed_updates=dp.resolve_used_update_types()


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
