import asyncio
import uvicorn
from app.bot import dp, bot
from app.db import init_db
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
    asyncio.create_task(start_bot())

    # Запускаем API (используем awaitable-версию uvicorn)
    print("📡 Запуск API...")
    uvicorn_config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())