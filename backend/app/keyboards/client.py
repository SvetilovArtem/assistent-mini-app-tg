from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== Обычное меню клиента =====
client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✂️ Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="❓ О нас"), KeyboardButton(text="📞 Контакты")]
    ],
    resize_keyboard=True
)

# ===== Меню клиента для админа (с кнопкой возврата) =====
client_menu_for_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✂️ Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="❓ О нас"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="🔙 Вернуться в админ-панель")]
    ],
    resize_keyboard=True
)