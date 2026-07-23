import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..config import config
from ..database import (
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

router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# FSM ДЛЯ ДОБАВЛЕНИЯ МАСТЕРА
# ============================================================

class MasterStates(StatesGroup):
    waiting_for_telegram_id = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_services = State()


# ============================================================
# МЕНЮ АДМИНА
# ============================================================

@router.message(F.text == "👑 Управление мастерами")
async def admin_masters_menu(message: types.Message):
    """Показывает список мастеров для управления."""
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
    for m in masters:
        status = "🟢" if m['is_active'] else "🔴"
        text += f"{status} {m['name']} (ID: {m['id']})\n"
        text += f"   🆔 {m['telegram_id']}\n"
        text += f"   📞 {m['phone'] or 'Не указан'}\n\n"
    
    await message.answer(text, reply_markup=get_admin_masters_keyboard())


def get_admin_masters_keyboard():
    """Клавиатура для управления мастерами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить мастера", callback_data="admin_add_master")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_back_to_menu")]
    ])


# ============================================================
# ДОБАВЛЕНИЕ МАСТЕРА (FSM)
# ============================================================

@router.callback_query(lambda c: c.data == "admin_add_master")
async def add_master_start(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления мастера."""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    await state.set_state(MasterStates.waiting_for_telegram_id)
    await callback.message.edit_text(
        "📝 **Добавление нового мастера**\n\n"
        "Введите **Telegram ID** мастера.\n"
        "Например: 123456789\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(MasterStates.waiting_for_telegram_id)
async def add_master_telegram_id(message: types.Message, state: FSMContext):
    """Получает Telegram ID мастера."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.")
        return
    
    try:
        telegram_id = int(message.text.strip())
        await state.update_data(telegram_id=telegram_id)
        await state.set_state(MasterStates.waiting_for_name)
        await message.answer(
            "📝 Введите **имя** мастера.\n"
            "Например: Анна",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (Telegram ID).")


@router.message(MasterStates.waiting_for_name)
async def add_master_name(message: types.Message, state: FSMContext):
    """Получает имя мастера."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.")
        return
    
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(MasterStates.waiting_for_phone)
    await message.answer(
        "📝 Введите **телефон** мастера (или отправьте «Пропустить»).\n"
        "Например: +7 999 123-45-67",
        parse_mode="Markdown"
    )


@router.message(MasterStates.waiting_for_phone)
async def add_master_phone(message: types.Message, state: FSMContext):
    """Получает телефон мастера."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление мастера отменено.")
        return
    
    phone = message.text.strip() if message.text != "Пропустить" else None
    await state.update_data(phone=phone)
    
    # Показываем список услуг для назначения
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
            "Когда закончите — нажмите «✅ Готово».",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # Если услуг нет — сразу создаём мастера
        await create_master_from_state(message, state)


@router.callback_query(MasterStates.waiting_for_services)
async def add_master_services(callback: types.CallbackQuery, state: FSMContext):
    """Выбирает услуги для мастера."""
    if callback.data == "admin_master_services_done":
        await create_master_from_state(callback.message, state)
        await callback.answer()
        return
    
    service_id = int(callback.data.replace("service_", ""))
    
    # Получаем текущий список выбранных услуг
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    
    if service_id in selected_services:
        selected_services.remove(service_id)
    else:
        selected_services.append(service_id)
    
    await state.update_data(selected_services=selected_services)
    
    # Обновляем клавиатуру с отметками
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
        "📝 **Выберите услуги** для мастера (можно несколько):\n"
        "Нажимайте на услуги, чтобы выбрать/отменить.\n"
        "Когда закончите — нажмите «✅ Готово».",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def create_master_from_state(message: types.Message, state: FSMContext):
    """Создаёт мастера из данных состояния."""
    data = await state.get_data()
    telegram_id = data.get('telegram_id')
    name = data.get('name')
    phone = data.get('phone')
    selected_services = data.get('selected_services', [])
    
    try:
        master_id = create_master(telegram_id, name, phone)
        
        # Назначаем услуги
        for service_id in selected_services:
            assign_service_to_master(master_id, service_id)
        
        await message.answer(
            f"✅ Мастер **{name}** создан!\n"
            f"🆔 Telegram ID: {telegram_id}\n"
            f"📞 Телефон: {phone or 'Не указан'}\n"
            f"✂️ Услуг: {len(selected_services)}",
            parse_mode="Markdown"
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


# ============================================================
# ПРОСМОТР ВСЕХ ЗАПИСЕЙ
# ============================================================

@router.message(F.text == "📊 Все записи")
async def admin_all_bookings(message: types.Message):
    """Показывает все записи по салону."""
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
    """Показывает статистику по салону."""
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
# ОБРАБОТКА НАЗАД
# ============================================================

@router.callback_query(lambda c: c.data == "admin_back_to_menu")
async def admin_back_to_menu(callback: types.CallbackQuery):
    """Возвращает админа в главное меню."""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=admin_menu  
    )
    await callback.answer()