from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Главное меню для МАСТЕРА =====
master_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💇 Мои слоты")],
        [KeyboardButton(text="➕ Добавить слот")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="🔙 В главное меню")]
    ],
    resize_keyboard=True
)
