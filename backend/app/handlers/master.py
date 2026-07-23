import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..config import config
from ..database import (
    get_master_by_telegram_id,
    get_master_slots,
    add_slot,
    delete_slot,
    toggle_slot_availability,
    get_user_bookings,
    get_all_bookings
)

router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# FSM ДЛЯ ДОБАВЛЕНИЯ СЛОТА
# ============================================================

class SlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()


# ============================================================
# МЕНЮ МАСТЕРА
# ============================================================

@router.message(F.text == "💇 Мои слоты")
async def master_slots_menu(message: types.Message):
    """Показывает все слоты мастера."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.")
        return
    
    slots = get_master_slots(master['id'])
    if not slots:
        await message.answer(
            "📅 У вас нет добавленных слотов.\n"
            "Нажмите «➕ Добавить слот» чтобы создать."
        )
        return
    
    text = "📅 **Ваши слоты:**\n\n"
    for s in slots[:20]:  # Показываем последние 20
        status = "🟢" if s['is_available'] else "🔴"
        text += f"{status} {s['date']} {s['time']}"
        if s['booking_id']:
            text += " 📌 (занято)"
        text += "\n"
    
    await message.answer(text, parse_mode="Markdown")


# ============================================================
# ДОБАВЛЕНИЕ СЛОТА (FSM)
# ============================================================

@router.message(F.text == "➕ Добавить слот")
async def add_slot_start(message: types.Message, state: FSMContext):
    """Начинает процесс добавления слота."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.")
        return
    
    await state.set_state(SlotStates.waiting_for_date)
    await message.answer(
        "📅 Введите дату в формате **ДД.ММ.ГГГГ**\n"
        "Например: 25.07.2026\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        parse_mode="Markdown"
    )


@router.message(SlotStates.waiting_for_date)
async def add_slot_date(message: types.Message, state: FSMContext):
    """Получает дату для слота."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление слота отменено.")
        return
    
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y")
        date_str = date_obj.strftime("%Y-%m-%d")
        await state.update_data(date=date_str)
        await state.set_state(SlotStates.waiting_for_time)
        await message.answer(
            "🕐 Введите время в формате **ЧЧ:ММ**\n"
            "Например: 14:00\n\n"
            "Или нажмите «❌ Отмена» чтобы отменить.",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте **ДД.ММ.ГГГГ**", parse_mode="Markdown")


@router.message(SlotStates.waiting_for_time)
async def add_slot_time(message: types.Message, state: FSMContext):
    """Получает время и сохраняет слот."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление слота отменено.")
        return
    
    try:
        datetime.strptime(message.text, "%H:%M")
        time_str = message.text
        
        data = await state.get_data()
        date_str = data.get('date')
        
        master = get_master_by_telegram_id(message.from_user.id)
        if not master:
            await message.answer("⛔ Вы не зарегистрированы как мастер.")
            await state.clear()
            return
        
        slot_id = add_slot(master['id'], date_str, time_str)
        
        await message.answer(
            f"✅ Слот добавлен!\n"
            f"📅 {date_str}\n"
            f"🕐 {time_str}",
            parse_mode="Markdown"
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте **ЧЧ:ММ**", parse_mode="Markdown")


# ============================================================
# УДАЛЕНИЕ СЛОТА
# ============================================================

@router.callback_query(lambda c: c.data and c.data.startswith("delete_slot_"))
async def delete_slot_callback(callback: types.CallbackQuery):
    """Удаляет слот (если на него нет записей)."""
    slot_id = int(callback.data.replace("delete_slot_", ""))
    master = get_master_by_telegram_id(callback.from_user.id)
    
    if not master:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    if delete_slot(slot_id, master['id']):
        await callback.answer("✅ Слот удалён")
        await callback.message.delete()
    else:
        await callback.answer("❌ Нельзя удалить слот с активной записью", show_alert=True)


# ============================================================
# ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ СЛОТА
# ============================================================

@router.callback_query(lambda c: c.data and c.data.startswith("toggle_slot_"))
async def toggle_slot_callback(callback: types.CallbackQuery):
    """Включает/выключает доступность слота."""
    slot_id = int(callback.data.replace("toggle_slot_", ""))
    master = get_master_by_telegram_id(callback.from_user.id)
    
    if not master:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    if toggle_slot_availability(slot_id, master['id']):
        await callback.answer("🔄 Статус слота изменён")
        # Обновляем сообщение со слотами
        await master_slots_menu(callback.message)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
# ПРОСМОТР ЗАПИСЕЙ МАСТЕРА
# ============================================================

@router.message(F.text == "📋 Мои записи")
async def master_bookings(message: types.Message):
    """Показывает мастеру его записи (клиентов)."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.")
        return
    
    bookings = get_all_bookings(master_id=master['id'])
    
    if not bookings:
        await message.answer("📭 У вас пока нет записей.")
        return
    
    text = "📋 **Ваши записи (клиенты):**\n\n"
    for b in bookings:
        text += (
            f"🆔 #{b['id']} | {b['username'] or 'Не указан'}\n"
            f"   ✂️ {b['service_name']}\n"
            f"   📅 {b['date']} в {b['time']}\n"
            f"   📞 {b['phone']}\n\n"
        )
    
    await message.answer(text, parse_mode="Markdown")


# ============================================================
# КНОПКА "НАЗАД" (В ГЛАВНОЕ МЕНЮ)
# ============================================================

@router.message(F.text == "🔙 В главное меню")
async def back_to_main_menu(message: types.Message):
    """Возвращает мастера в главное меню."""
    await message.answer(
        "Главное меню:",
        reply_markup=message.bot.keyboard  # Здесь должна быть клавиатура мастера
    )