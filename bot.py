# bot.py — Точка входа бота

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import init_db
from scheduler import scheduler, restore_reminders

# Импорт роутеров
from handlers.start import router as start_router
from middleware import UserManagementMiddleware
from handlers.booking import router as booking_router
from handlers.cancel import router as cancel_router
from handlers.prices import router as prices_router
from handlers.portfolio import router as portfolio_router
from handlers.location import router as location_router
from handlers.waitlist import router as waitlist_router
from handlers.review import router as review_router
from handlers.admin import router as admin_router


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    # Инициализация базы данных
    await init_db()
    print("✅ База данных инициализирована")

    # Запускаем планировщик
    scheduler.start()
    print("✅ Планировщик запущен")

    # Восстанавливаем напоминания из БД
    await restore_reminders(bot)
    print("✅ Напоминания восстановлены")

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    print(f"✅ Бот @{bot_info.username} запущен!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    scheduler.shutdown(wait=False)
    print("🛑 Бот остановлен")


async def main():
    """Главная функция запуска бота."""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Создание бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация middleware
    dp.update.middleware(UserManagementMiddleware())

    # Регистрация роутеров (порядок важен!)
    dp.include_routers(
        start_router,
        booking_router,
        cancel_router,
        prices_router,
        portfolio_router,
        location_router,
        waitlist_router,
        review_router,
        admin_router,
    )

    # Регистрация событий запуска/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Удаляем вебхук (если был) и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
