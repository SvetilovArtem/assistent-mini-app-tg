import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..config import config
from ..db import get_master_by_telegram_id
from ..keyboards.client import client_menu, client_menu_for_admin
from ..keyboards.master import master_menu, master_menu_for_admin
from ..keyboards.admin import admin_menu

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start с поддержкой виртуальной роли."""
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    # Проверяем, есть ли виртуальная роль (для разработки)
    data = await state.get_data()
    dev_role = data.get('dev_role')
    
    # Определяем роль и выбираем меню
    if dev_role:
        role = dev_role
        role_display = {
            "client": "🧑 Клиент (виртуальный)",
            "master": "💇 Мастер (виртуальный)",
            "admin": "👑 Админ (виртуальный)"
        }.get(dev_role, "🧑 Клиент")
        
        # Для админа в виртуальной роли показываем специальные меню с кнопкой возврата
        if dev_role == "client":
            reply_markup = client_menu_for_admin
        elif dev_role == "master":
            reply_markup = master_menu_for_admin
        else:
            reply_markup = admin_menu
    else:
        # Реальная роль
        if is_admin:
            role = "admin"
            role_display = "👑 Супер-админ"
            reply_markup = admin_menu
        elif master:
            role = "master"
            role_display = f"💇 Мастер {master['name']}"
            reply_markup = master_menu
        else:
            role = "client"
            role_display = "🧑 Клиент"
            reply_markup = client_menu
    
    await message.answer(
        f"👋 Добро пожаловать в салон «{config.SALON_NAME}»!\n\n"
        f"Ваша роль: {role_display}\n\n"
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


# ============================================================
# ВОЗВРАТ В АДМИН-ПАНЕЛЬ (ДЛЯ АДМИНА В ВИРТУАЛЬНОЙ РОЛИ)
# ============================================================

@router.message(F.text == "🔙 Вернуться в админ-панель")
async def back_to_admin_panel(message: types.Message, state: FSMContext):
    """Возвращает админа из виртуальной роли в админ-меню."""
    user_id = message.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    # Сбрасываем виртуальную роль
    await state.clear()
    
    await message.answer(
        "✅ Вы вернулись в админ-панель.",
        reply_markup=admin_menu
    )


# ============================================================
# ПЕРЕКЛЮЧЕНИЕ РОЛЕЙ (ТОЛЬКО ДЛЯ АДМИНА)
# ============================================================

@router.message(Command("switch"))
@router.message(F.text == "🔄 Изменить роль")
async def change_role_panel(message: types.Message, state: FSMContext):
    """Панель переключения ролей (команда или кнопка)."""
    user_id = message.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён. Только для супер-админа.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Клиент", callback_data="switch_client")],
        [InlineKeyboardButton(text="💇 Мастер", callback_data="switch_master")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="switch_admin")],
        [InlineKeyboardButton(text="🔄 Сбросить (реальная роль)", callback_data="switch_reset")]
    ])
    
    await message.answer(
        "🔄 **Переключение ролей (режим разработки)**\n\n"
        "Выберите роль, которую хотите тестировать:\n"
        "• 👤 Клиент — запись, мои записи\n"
        "• 💇 Мастер — слоты, записи клиентов\n"
        "• 👑 Админ — полный доступ\n\n"
        "⚠️ После выбора напишите /start для обновления меню.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("switch_"))
async def switch_role_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор роли."""
    user_id = callback.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    role_map = {
        "switch_client": "client",
        "switch_master": "master",
        "switch_admin": "admin",
        "switch_reset": None
    }
    
    role = role_map.get(callback.data)
    
    if role is None:
        await state.clear()
        await callback.message.edit_text(
            "✅ Роль сброшена. Теперь бот будет определять вашу роль по базе данных.\n"
            "Напишите /start для обновления меню."
        )
    else:
        await state.update_data(dev_role=role)
        await callback.message.edit_text(
            f"✅ Роль переключена на **{role.capitalize()}**.\n"
            f"Напишите /start для обновления меню.",
            parse_mode="Markdown"
        )
    
    await callback.answer()


# ============================================================
# ОБЩИЕ ОБРАБОТЧИКИ
# ============================================================

@router.message(F.text == "❌ Отмена")
async def cancel_action(message: types.Message, state: FSMContext):
    """Обрабатывает кнопку '❌ Отмена' — очищает состояние FSM."""
    current_state = await state.get_state()
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    if is_admin:
        reply_markup = admin_menu
    elif master:
        reply_markup = master_menu
    else:
        reply_markup = client_menu
    
    if current_state:
        await state.clear()
        await message.answer(
            "✅ Действие отменено.",
            reply_markup=reply_markup
        )
    else:
        await message.answer(
            "❌ Нет активного действия для отмены.",
            reply_markup=reply_markup
        )


@router.message(F.text == "🔙 В главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    """Возвращает пользователя в его главное меню (сбрасывает состояние)."""
    await state.clear()
    user_id = message.from_user.id
    is_admin = user_id in config.ADMIN_IDS
    master = get_master_by_telegram_id(user_id)
    
    if is_admin:
        reply_markup = admin_menu
    elif master:
        reply_markup = master_menu
    else:
        reply_markup = client_menu
    
    await message.answer(
        "Главное меню:",
        reply_markup=reply_markup
    )


@router.message()
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений."""
    await message.answer(
        "⚠️ Я не понимаю эту команду.\n"
        "Используйте кнопки меню или команду /help."
    )