import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from ..config import config
from ..db import (
    get_all_masters,
    get_all_bookings,
    get_statistics,
    create_master,
    update_master,
    get_master_by_telegram_id,
    get_all_services,
    assign_service_to_master,
    get_master_services
)
from ..keyboards.admin import admin_menu
from ..utils import get_user_by_username

router = Router()
logger = logging.getLogger(__name__)

# Клавиатура с кнопкой "Отмена"
CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)


# ============================================================
# FSM ДЛЯ ДОБАВЛЕНИЯ МАСТЕРА
# ============================================================

class MasterStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_services = State()


# ============================================================
# FSM ДЛЯ РЕДАКТИРОВАНИЯ МАСТЕРА
# ============================================================

class EditMasterStates(StatesGroup):
    choosing_field = State()
    waiting_for_name = State()
    waiting_for_phone = State()


# ============================================================
# МЕНЮ АДМИНА
# ============================================================

@router.message(F.text == "👑 Управление мастерами")
async def admin_masters_menu(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    masters = get_all_masters(active_only=False)
    
    if not masters:
        await message.answer(
            "📭 Список мастеров пуст.\n"
            "Нажмите «➕ Добавить мастера» чтобы создать.",
            reply_markup=get_admin_masters_keyboard()
        )
        return
    
    text = "👑 **Управление мастерами:**\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for m in masters:
        status = "🟢" if m['is_active'] else "🔴"
        text += f"{status} {m['name']} (ID: {m['id']})\n"
        text += f"   🆔 Telegram: {m['telegram_id'] or 'Не привязан'}\n"
        text += f"   📞 Телефон: {m['phone'] or 'Не указан'}\n"
        text += f"   ✂️ Услуг: {len(get_master_services(m['id']))}\n"
        text += f"   {'✅ Активен' if m['is_active'] else '❌ Неактивен'}\n\n"
        
        row = []
        row.append(InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"edit_master_{m['id']}"
        ))
        row.append(InlineKeyboardButton(
            text="📋 Записи",
            callback_data=f"view_master_{m['id']}"
        ))
        if m['is_active']:
            row.append(InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"delete_master_{m['id']}"
            ))
        keyboard.inline_keyboard.append(row)
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="➕ Добавить мастера", callback_data="admin_add_master")
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


def get_admin_masters_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить мастера", callback_data="admin_add_master")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_back_to_menu")]
    ])


# ============================================================
# ПРОСМОТР ЗАПИСЕЙ МАСТЕРА
# ============================================================

@router.callback_query(lambda c: c.data and c.data.startswith("view_master_"))
async def view_master_bookings(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    master_id = int(callback.data.replace("view_master_", ""))
    masters = get_all_masters(active_only=False)
    master = next((m for m in masters if m['id'] == master_id), None)
    
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
    
    bookings = get_all_bookings(master_id=master_id, limit=50)
    
    if not bookings:
        await callback.message.edit_text(
            f"📭 У мастера **{master['name']}** пока нет записей.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к мастерам", callback_data="admin_masters_back")]
            ]),
            parse_mode="Markdown"
        )
        return
    
    text = f"📋 **Записи мастера {master['name']}:**\n\n"
    for b in bookings:
        text += (
            f"🆔 #{b['id']} | {b['username'] or 'Не указан'}\n"
            f"   ✂️ {b['service_name']}\n"
            f"   📅 {b['date']} в {b['time']}\n"
            f"   📞 {b['phone']}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к мастерам", callback_data="admin_masters_back")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_masters_back")
async def admin_masters_back(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await admin_masters_menu(callback.message)
    await callback.answer()


# ============================================================
# УДАЛЕНИЕ МАСТЕРА
# ============================================================

@router.callback_query(lambda c: c.data and c.data.startswith("delete_master_"))
async def delete_master(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    master_id = int(callback.data.replace("delete_master_", ""))
    bookings = get_all_bookings(master_id=master_id, limit=1)
    
    if bookings:
        await callback.answer(
            "❌ Нельзя удалить мастера с активными записями!",
            show_alert=True
        )
        return
    
    success = update_master(master_id, is_active=False)
    if success:
        await callback.answer("✅ Мастер удалён!", show_alert=True)
        await admin_masters_menu(callback.message)
    else:
        await callback.answer("❌ Ошибка при удалении мастера.", show_alert=True)


# ============================================================
# РЕДАКТИРОВАНИЕ МАСТЕРА
# ============================================================

@router.callback_query(lambda c: c.data and c.data.startswith("edit_master_"))
async def edit_master_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    master_id = int(callback.data.replace("edit_master_", ""))
    masters = get_all_masters(active_only=False)
    master = next((m for m in masters if m['id'] == master_id), None)
    
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
    
    await state.update_data(edit_master_id=master_id)
    await state.set_state(EditMasterStates.choosing_field)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить имя", callback_data="edit_field_name")],
        [InlineKeyboardButton(text="📞 Изменить телефон", callback_data="edit_field_phone")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="edit_back_to_masters")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")]
    ])
    
    await callback.message.answer(
        f"✏️ **Редактирование мастера {master['name']}**\n\n"
        f"📝 Имя: **{master['name']}**\n"
        f"📞 Телефон: **{master['phone'] or 'Не указан'}**\n\n"
        f"Что хотите изменить?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(EditMasterStates.choosing_field)
async def edit_choose_field(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    data = await state.get_data()
    master_id = data.get('edit_master_id')
    masters = get_all_masters(active_only=False)
    master = next((m for m in masters if m['id'] == master_id), None)
    
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
    
    if callback.data == "edit_cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("❌ Редактирование отменено.")
        await callback.answer()
        return
    
    if callback.data == "edit_back_to_masters":
        await state.clear()
        await admin_masters_menu(callback.message)
        await callback.answer()
        return
    
    if callback.data == "edit_field_name":
        await state.set_state(EditMasterStates.waiting_for_name)
        await callback.message.delete()
        await callback.message.answer(
            f"📝 **Введите новое имя** для мастера **{master['name']}**:\n\n"
            f"Или нажмите «❌ Отмена» чтобы отменить.",
            reply_markup=CANCEL_KB,
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    if callback.data == "edit_field_phone":
        await state.set_state(EditMasterStates.waiting_for_phone)
        await callback.message.delete()
        await callback.message.answer(
            f"📞 **Введите новый телефон** для мастера **{master['name']}** (с +):\n"
            f"Например: +7 999 123-45-67\n\n"
            f"Или нажмите «❌ Отмена» чтобы отменить.",
            reply_markup=CANCEL_KB,
            parse_mode="Markdown"
        )
        await callback.answer()
        return


@router.message(EditMasterStates.waiting_for_name)
async def edit_master_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Редактирование отменено.", reply_markup=admin_menu)
        return
    
    data = await state.get_data()
    master_id = data.get('edit_master_id')
    if not master_id:
        await state.clear()
        await message.answer("❌ Ошибка: мастер не найден.", reply_markup=admin_menu)
        return
    
    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer(
            "❌ Слишком короткое имя. Введите хотя бы 2 символа.",
            reply_markup=CANCEL_KB
        )
        return
    
    success = update_master(master_id, name=new_name)
    if success:
        await show_edit_success(message, state, master_id)
    else:
        await message.answer("❌ Ошибка при обновлении имени.", reply_markup=admin_menu)
        await state.clear()


@router.message(EditMasterStates.waiting_for_phone)
async def edit_master_phone(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Редактирование отменено.", reply_markup=admin_menu)
        return
    
    data = await state.get_data()
    master_id = data.get('edit_master_id')
    if not master_id:
        await state.clear()
        await message.answer("❌ Ошибка: мастер не найден.", reply_markup=admin_menu)
        return
    
    new_phone = message.text.strip()
    if not new_phone.startswith('+') or not any(c.isdigit() for c in new_phone):
        await message.answer(
            "❌ Неверный формат телефона. Введите номер с +.",
            reply_markup=CANCEL_KB
        )
        return
    
    success = update_master(master_id, phone=new_phone)
    if success:
        await show_edit_success(message, state, master_id)
    else:
        await message.answer("❌ Ошибка при обновлении телефона.", reply_markup=admin_menu)
        await state.clear()


async def show_edit_success(message: types.Message, state: FSMContext, master_id: int):
    masters = get_all_masters(active_only=False)
    master = next((m for m in masters if m['id'] == master_id), None)
    if not master:
        await message.answer("❌ Мастер не найден.", reply_markup=admin_menu)
        await state.clear()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить имя", callback_data="edit_field_name")],
        [InlineKeyboardButton(text="📞 Изменить телефон", callback_data="edit_field_phone")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="edit_done")]
    ])
    
    await state.set_state(EditMasterStates.choosing_field)
    await message.answer(
        f"✅ Данные обновлены!\n\n"
        f"✏️ **Редактирование мастера {master['name']}**\n\n"
        f"📝 Имя: **{master['name']}**\n"
        f"📞 Телефон: **{master['phone'] or 'Не указан'}**\n\n"
        f"Что хотите изменить дальше?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data == "edit_done")
async def edit_done(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.clear()
    await admin_masters_menu(callback.message)
    await callback.answer()


# ============================================================
# ДОБАВЛЕНИЕ МАСТЕРА
# ============================================================

@router.callback_query(lambda c: c.data == "admin_add_master")
async def add_master_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.set_state(MasterStates.waiting_for_username)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        "📝 Добавление нового мастера\n\n"
        "Введите username мастера в Telegram (с @ или без).\n"
        "Например: @anna_master\n\n"
        "Если username не публичный — введите Telegram ID (число).\n\n"
        "💡 Узнать свой ID можно у бота @userinfobot.\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=CANCEL_KB
    )
    await callback.answer()
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.set_state(MasterStates.waiting_for_username)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        "📝 **Добавление нового мастера**\n\n"
        "Введите **username** мастера в Telegram (с @ или без).\n"
        "Например: @anna_master\n\n"
        "Если username не публичный — введите **Telegram ID** (число).\n\n"
        "💡 Узнать свой ID можно у бота @userinfobot.\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=CANCEL_KB,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(MasterStates.waiting_for_username)
async def add_master_username(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.", reply_markup=admin_menu)
        return
    
    input_text = message.text.strip()
    user = None
    telegram_id = None
    
    # Пробуем найти по username
    if not input_text.isdigit():
        user = await get_user_by_username(input_text, bot)
        if user:
            telegram_id = user.id
            await message.answer(
                f"✅ Найден пользователь: {user.first_name} (@{user.username or 'без username'})\n"
                f"🆔 ID: {user.id}\n\n"
                "Теперь введите **имя** мастера:",
                reply_markup=CANCEL_KB
            )
            await state.update_data(telegram_id=telegram_id)
            await state.set_state(MasterStates.waiting_for_name)
            return
    
    # Если username не найден или введено число — пробуем как ID
    if input_text.isdigit():
        try:
            user = await bot.get_chat(int(input_text))
            telegram_id = user.id
            await message.answer(
                f"✅ Найден пользователь: {user.first_name} (@{user.username or 'без username'})\n"
                f"🆔 ID: {user.id}\n\n"
                "Теперь введите **имя** мастера:",
                reply_markup=CANCEL_KB
            )
            await state.update_data(telegram_id=telegram_id)
            await state.set_state(MasterStates.waiting_for_name)
            return
        except Exception:
            pass
    
    # Если ничего не найдено
    await message.answer(
        "❌ Пользователь не найден.\n\n"
        "Проверьте правильность username или ID.\n\n"
        "💡 Узнать свой ID можно у бота @userinfobot.\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=CANCEL_KB
    )


@router.message(MasterStates.waiting_for_name)
async def add_master_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.", reply_markup=admin_menu)
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(
            "❌ Слишком короткое имя. Введите хотя бы 2 символа.",
            reply_markup=CANCEL_KB
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(MasterStates.waiting_for_phone)
    await message.answer(
        "📝 Введите **телефон** мастера (с +).\n"
        "Например: +7 999 123-45-67\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=CANCEL_KB,
        parse_mode="Markdown"
    )


@router.message(MasterStates.waiting_for_phone)
async def add_master_phone(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.", reply_markup=admin_menu)
        return
    
    phone = message.text.strip()
    if not phone.startswith('+') or not any(c.isdigit() for c in phone):
        await message.answer(
            "❌ Неверный формат телефона. Введите номер с +.",
            reply_markup=CANCEL_KB
        )
        return
    
    await state.update_data(phone=phone)
    
    services = get_all_services(active_only=True)
    if services:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=s['name'], callback_data=f"service_{s['id']}")]
            for s in services
        ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data="admin_master_services_done")])
        
        await state.set_state(MasterStates.waiting_for_services)
        await message.answer(
            "📝 **Выберите услуги** для мастера (можно несколько):\n"
            "Нажимайте на услуги, чтобы выбрать/отменить.\n"
            "Когда закончите — нажмите «✅ Готово».\n\n"
            "Или нажмите «❌ Отмена» чтобы отменить.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await create_master_from_state(message, state)


@router.callback_query(MasterStates.waiting_for_services)
async def add_master_services(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "admin_master_services_done":
        await create_master_from_state(callback.message, state)
        await callback.answer()
        return
    
    service_id = int(callback.data.replace("service_", ""))
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    
    if service_id in selected_services:
        selected_services.remove(service_id)
    else:
        selected_services.append(service_id)
    
    await state.update_data(selected_services=selected_services)
    
    services = get_all_services(active_only=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ {s['name']}" if s['id'] in selected_services else s['name'],
            callback_data=f"service_{s['id']}"
        )]
        for s in services
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data="admin_master_services_done")])
    
    await callback.message.edit_text(
        "📝 **Выберите услуги** для мастера:\n"
        "Нажимайте на услуги, чтобы выбрать/отменить.\n"
        "Когда закончите — нажмите «✅ Готово».\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def create_master_from_state(message: types.Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = data.get('telegram_id', 0)
    name = data.get('name')
    phone = data.get('phone')
    selected_services = data.get('selected_services', [])
    
    try:
        master_id = create_master(telegram_id, name, phone)
        
        for service_id in selected_services:
            assign_service_to_master(master_id, service_id)
        
        await message.answer(
            f"✅ Мастер **{name}** создан!\n"
            f"🆔 Telegram ID: {telegram_id or 'Не привязан'}\n"
            f"📞 Телефон: {phone}\n"
            f"✂️ Услуг: {len(selected_services)}",
            reply_markup=admin_menu,
            parse_mode="Markdown"
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


# ============================================================
# ВСЕ ЗАПИСИ
# ============================================================

@router.message(F.text == "📊 Все записи")
async def admin_all_bookings(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    bookings = get_all_bookings(limit=30)
    if not bookings:
        await message.answer("📭 Нет активных записей.")
        return
    
    text = "📊 **Все записи (последние 30):**\n\n"
    for b in bookings:
        text += (
            f"🆔 #{b['id']} | {b['username'] or 'Не указан'}\n"
            f"   ✂️ {b['service_name']}\n"
            f"   💇 {b['master_name']}\n"
            f"   📅 {b['date']} в {b['time']}\n"
            f"   📞 {b['phone']}\n\n"
        )
    
    await message.answer(text, parse_mode="Markdown")


# ============================================================
# СТАТИСТИКА
# ============================================================

@router.message(F.text == "📈 Статистика")
async def admin_statistics(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    stats = get_statistics()
    text = (
        "📈 **Статистика салона:**\n\n"
        f"📌 Всего записей: {stats['total']}\n"
        f"✅ Активных: {stats['active']}\n"
        f"❌ Отменённых: {stats['cancelled']}\n"
        f"📅 На сегодня: {stats['today']}\n\n"
        f"📆 Мастеров: {len(get_all_masters(active_only=True))}"
    )
    
    await message.answer(text, parse_mode="Markdown")


# ============================================================
# ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
# ============================================================

@router.callback_query(lambda c: c.data == "admin_back_to_menu")
async def admin_back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=admin_menu
    )
    await callback.answer()