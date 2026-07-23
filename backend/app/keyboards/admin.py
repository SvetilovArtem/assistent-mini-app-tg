from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Главное меню для АДМИНА =====
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Все записи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="👑 Управление мастерами")],
        [KeyboardButton(text="🔙 В главное меню")]
    ],
    resize_keyboard=True
)