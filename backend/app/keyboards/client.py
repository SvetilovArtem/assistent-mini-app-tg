from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Главное меню для КЛИЕНТА =====
client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✂️ Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="❓ О нас"), KeyboardButton(text="📞 Контакты")]
    ],
    resize_keyboard=True
)
