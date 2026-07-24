from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Обычное меню мастера =====
master_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💇 Мои слоты")],
        [KeyboardButton(text="➕ Добавить слот")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="🔙 В главное меню")]
    ],
    resize_keyboard=True
)

# ===== Меню мастера для админа (с кнопкой возврата) =====
master_menu_for_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💇 Мои слоты")],
        [KeyboardButton(text="➕ Добавить слот")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="🔙 В главное меню")],
        [KeyboardButton(text="🔙 Вернуться в админ-панель")]
    ],
    resize_keyboard=True
)