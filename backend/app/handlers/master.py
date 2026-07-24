import logging
import re
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from ..config import config
from ..db.queries import (
    get_master_by_telegram_id,
    get_master_slots,
    add_slot,
    delete_slot,
    toggle_slot_availability,
    get_user_bookings,
    get_all_bookings
)
from ..keyboards.master import master_menu

router = Router()
logger = logging.getLogger(__name__)

# Клавиатура с кнопкой "Отмена"
CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def parse_time(time_str: str) -> str:
    """
    Парсит время из разных форматов и возвращает в ЧЧ:ММ.
    Поддерживает: 9:00, 9.00, 9-00, 09:00, 9.00, 9-00, 900 (как 09:00)
    """
    time_str = time_str.strip()
    
    if time_str.isdigit() and len(time_str) in (3, 4):
        if len(time_str) == 3:
            time_str = f"0{time_str[0]}:{time_str[1:]}"
        else:
            time_str = f"{time_str[:2]}:{time_str[2:]}"
        return time_str
    
    time_str = re.sub(r'[.\- ]', ':', time_str)
    
    if ':' not in time_str:
        raise ValueError("Неверный формат времени")
    
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        return dt.strftime("%H:%M")
    except ValueError:
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            return dt.strftime("%H:%M")
        except ValueError:
            raise ValueError("Неверный формат времени")


# ============================================================
# FSM ДЛЯ ДОБАВЛЕНИЯ СЛОТА
# ============================================================

class SlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()


# ============================================================
# МЕНЮ МАСТЕРА
# ============================================================

@router.message(F.text == "💇 Мои слоты")
async def master_slots_menu(message: types.Message):
    """Показывает все слоты мастера."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.", reply_markup=master_menu)
        return
    
    slots = get_master_slots(master['id'])
    if not slots:
        await message.answer(
            "📅 У вас нет добавленных слотов.\n"
            "Нажмите «➕ Добавить слот» чтобы создать.",
            reply_markup=master_menu
        )
        return
    
    text = "📅 Ваши слоты:\n\n"
    for s in slots[:20]:
        status = "🟢" if s['is_available'] else "🔴"
        time_range = f"{s['time']} - {s['end_time']}" if s.get('end_time') else s['time']
        text += f"{status} {s['date']} {time_range}"
        if s['booking_id']:
            text += " 📌 (занято)"
        text += "\n"
    
    await message.answer(text, reply_markup=master_menu)


# ============================================================
# ДОБАВЛЕНИЕ СЛОТА (FSM)
# ============================================================

@router.message(F.text == "➕ Добавить слот")
async def add_slot_start(message: types.Message, state: FSMContext):
    """Начинает процесс добавления слота."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.", reply_markup=master_menu)
        return
    
    await state.set_state(SlotStates.waiting_for_date)
    await message.answer(
        "📅 Введите дату в формате ДД.ММ.ГГГГ\n"
        "Например: 25.07.2026\n\n"
        "Или нажмите «❌ Отмена» чтобы отменить.",
        reply_markup=CANCEL_KB
    )


@router.message(SlotStates.waiting_for_date)
async def add_slot_date(message: types.Message, state: FSMContext):
    """Получает дату слота."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление слота отменено.", reply_markup=master_menu)
        return
    
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y")
        date_str = date_obj.strftime("%Y-%m-%d")
        await state.update_data(date=date_str)
        await state.set_state(SlotStates.waiting_for_start_time)
        await message.answer(
            "🕐 Введите время начала слота в формате ЧЧ:ММ\n"
            "Например: 13:00\n\n"
            "Или нажмите «❌ Отмена» чтобы отменить.",
            reply_markup=CANCEL_KB
        )
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ")


@router.message(SlotStates.waiting_for_start_time)
async def add_slot_start_time(message: types.Message, state: FSMContext):
    """Получает время начала слота."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление слота отменено.", reply_markup=master_menu)
        return
    
    try:
        start_time = parse_time(message.text)
        await state.update_data(start_time=start_time)
        await state.set_state(SlotStates.waiting_for_end_time)
        await message.answer(
            "🕐 Введите время окончания слота в формате ЧЧ:ММ\n"
            "Например: 14:00\n\n"
            "Или нажмите «❌ Отмена» чтобы отменить.",
            reply_markup=CANCEL_KB
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Поддерживаются форматы:\n"
            "• 9:00, 09:00\n"
            "• 9.00, 09.00\n"
            "• 9-00, 09-00\n"
            "• 900 (как 09:00)\n\n"
            "Попробуйте снова:"
        )


@router.message(SlotStates.waiting_for_end_time)
async def add_slot_end_time(message: types.Message, state: FSMContext):
    """Получает время окончания слота и сохраняет с проверкой пересечения."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление слота отменено.", reply_markup=master_menu)
        return
    
    try:
        end_time = parse_time(message.text)
        
        data = await state.get_data()
        date_str = data.get('date')
        start_time = data.get('start_time')
        
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        
        if end_dt <= start_dt:
            await message.answer(
                "❌ Время окончания должно быть позже времени начала.\n"
                "Пожалуйста, введите время окончания заново:"
            )
            return
        
        master = get_master_by_telegram_id(message.from_user.id)
        if not master:
            await message.answer("⛔ Вы не зарегистрированы как мастер.", reply_markup=master_menu)
            await state.clear()
            return
        
        try:
            slot_id = add_slot(master['id'], date_str, start_time, end_time)
            
            await message.answer(
                f"✅ Слот добавлен!\n"
                f"📅 {date_str}\n"
                f"🕐 {start_time} - {end_time}",
                reply_markup=master_menu
            )
            await state.clear()
            
        except ValueError as e:
            await message.answer(
                f"❌ {str(e)}\n\n"
                f"Пожалуйста, введите другое время окончания:",
                reply_markup=CANCEL_KB
            )
            return
        except Exception as e:
            logger.error(f"Ошибка при добавлении слота: {e}")
            await message.answer(
                f"❌ Произошла ошибка: {str(e)}\n\n"
                "Пожалуйста, попробуйте ещё раз или обратитесь к администратору.",
                reply_markup=CANCEL_KB
            )
            return
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Поддерживаются форматы:\n"
            "• 9:00, 09:00\n"
            "• 9.00, 09.00\n"
            "• 9-00, 09-00\n"
            "• 900 (как 09:00)\n\n"
            "Пожалуйста, введите время окончания заново:",
            reply_markup=CANCEL_KB
        )
        return


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
        await master_slots_menu(callback.message)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
# ПРОСМОТР ЗАПИСЕЙ МАСТЕРА
# ============================================================

@router.message(F.text == "📋 Мои записи")
async def show_my_bookings(message: types.Message):
    """Показывает записи: для клиента — его записи, для мастера — его клиентов."""
    user_id = message.from_user.id
    master = get_master_by_telegram_id(user_id)
    
    if master:
        bookings = get_all_bookings(master_id=master['id'])
        title = "📋 Ваши записи (клиенты):"
        reply_markup = master_menu
    else:
        bookings = get_user_bookings(user_id)
        title = "📋 Ваши записи:"
        reply_markup = None
    
    if not bookings:
        await message.answer("📭 У вас пока нет записей.", reply_markup=reply_markup)
        return
    
    text = f"{title}\n\n"
    for b in bookings:
        text += (
            f"🆔 #{b['id']} | {b['username'] or 'Не указан'}\n"
            f"   ✂️ {b['service_name']}\n"
            f"   📅 {b['date']} в {b['time']}\n"
            f"   📞 {b['phone']}\n\n"
        )
    
    await message.answer(text, reply_markup=reply_markup)


# ============================================================
# КНОПКА "НАЗАД" (В ГЛАВНОЕ МЕНЮ)
# ============================================================

@router.message(F.text == "🔙 В главное меню")
async def back_to_main_menu(message: types.Message):
    """Возвращает мастера в главное меню."""
    await message.answer(
        "Главное меню:",
        reply_markup=master_menu
    )