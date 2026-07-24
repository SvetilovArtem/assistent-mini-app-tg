from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Главное меню для АДМИНА =====
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Все записи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="👑 Управление мастерами")],
        [KeyboardButton(text="🔄 Изменить роль")]
    ],
    resize_keyboard=True
)