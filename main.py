import asyncio
from aiogram import Bot, Dispatcher

from app.handlers import router
from config import BOT_TOKEN


async def main():
    print('Бот запущен')
    bot = Bot(token=BOT_TOKEN)
    # обработчик
    dp = Dispatcher()
    # подключаем импортированный роутер из другого файла
    dp.include_router(router)
    # начинает полинг = опрашивает сервер телеграм
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
