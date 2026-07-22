import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from ..config import config
from ..database import get_master_by_telegram_id

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    # Кнопка для открытия Mini App
    webapp_btn = KeyboardButton(
        text="✂️ Открыть приложение",
        web_app=WebAppInfo(url=config.WEBAPP_URL)
    )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[webapp_btn]],
        resize_keyboard=True
    )
    
    # Определяем роль
    if is_admin:
        role = "👑 Супер-админ"
    elif master:
        role = f"💇 Мастер {master['name']}"
    else:
        role = "🧑 Клиент"
    
    await message.answer(
        f"👋 Добро пожаловать в салон «{config.SALON_NAME}»!\n\n"
        f"Ваша роль: {role}\n\n"
        f"📱 Нажмите кнопку ниже, чтобы открыть приложение.",
        reply_markup=keyboard
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    help_text = (
        "❓ **Помощь по боту**\n\n"
        "/start — запустить бота\n"
        "/help — эта справка\n\n"
        "🔹 Клиенты: могут записываться через приложение\n"
        "🔹 Мастера: управляют своими слотами\n"
        "🔹 Админы: управляют всем"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message()
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений."""
    await message.answer(
        "⚠️ Я не понимаю эту команду.\n"
        "Используйте кнопки меню или команду /help."
    )