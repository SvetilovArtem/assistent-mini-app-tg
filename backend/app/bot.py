import logging
from aiogram import Bot, Dispatcher
from .config import config
from .handlers import common, client, master, admin

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Создаём бота
bot = Bot(token=config.BOT_TOKEN)

# Создаём диспетчер
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(admin.router)
dp.include_router(client.router)   
dp.include_router(master.router) 
dp.include_router(common.router)    

print("✅ Бот инициализирован")