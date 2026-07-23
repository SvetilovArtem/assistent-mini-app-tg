import asyncio
import uvicorn
from app.bot import dp, bot
from app.database import init_db
from app.config import config


async def start_bot():
    """Запускает поллинг бота."""
    print("🤖 Запуск бота...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")


async def main():
    """Главная функция."""
    config.ensure_dirs()
    init_db()
    print("✅ База данных готова")

    # Запускаем бота в фоне
    bot_task = asyncio.create_task(start_bot())

    # Запускаем API (блокирующий)
    print("📡 Запуск API...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.API_PORT, reload=False)


if __name__ == "__main__":
    asyncio.run(main())
