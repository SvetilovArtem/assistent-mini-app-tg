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


if __name__ == "__main__":
    config.ensure_dirs()
    init_db()
    print("✅ База данных готова")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_bot())

    print("📡 Запуск API...")
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)