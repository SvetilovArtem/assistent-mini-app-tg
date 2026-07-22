import asyncio
import uvicorn
from app.bot import dp, bot
from app.database import init_db
from app.config import config

async def start_bot():
    print("🤖 Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    config.ensure_dirs()
    init_db()
    print("✅ База данных готова")
    
    # Запускаем бота в фоне
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_bot())
    
    # Запускаем API
    print("📡 Запуск API...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)