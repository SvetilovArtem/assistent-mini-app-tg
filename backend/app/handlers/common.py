import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from ..config import config
from ..db.queries import get_master_by_telegram_id
from ..keyboards.client import client_menu
from ..keyboards.master import master_menu
from ..keyboards.admin import admin_menu

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    # Кнопка для Mini App (опционально)
    webapp_btn = KeyboardButton(
        text="✂️ Открыть приложение",
        web_app=WebAppInfo(url=config.WEBAPP_URL)
    )
    
    if is_admin:
        role = "👑 Супер-админ"
        # Добавляем кнопку Mini App в админ-меню
        keyboard = admin_menu.keyboard + [[webapp_btn]]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    elif master:
        role = f"💇 Мастер {master['name']}"
        keyboard = master_menu.keyboard + [[webapp_btn]]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    else:
        role = "🧑 Клиент"
        keyboard = client_menu.keyboard + [[webapp_btn]]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    await message.answer(
        f"👋 Добро пожаловать в салон «{config.SALON_NAME}»!\n\n"
        f"Ваша роль: {role}\n\n"
        f"Используйте кнопки меню для действий.",
        reply_markup=reply_markup
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    await message.answer(
        "❓ **Помощь по боту**\n\n"
        "/start — запустить бота\n"
        "/help — эта справка\n\n"
        "🔹 Клиенты: могут записываться\n"
        "🔹 Мастера: управляют своими слотами\n"
        "🔹 Админы: управляют всем"
    )


@router.message()
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений."""
    await message.answer(
        "⚠️ Я не понимаю эту команду.\n"
        "Используйте кнопки меню или команду /help."
    )