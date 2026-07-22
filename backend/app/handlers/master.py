import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..database import get_master_by_telegram_id, get_master_slots, add_slot, delete_slot, toggle_slot_availability

router = Router()
logger = logging.getLogger(__name__)


class SlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()


@router.message(F.text == "💇 Мои слоты")
async def master_slots_menu(message: types.Message):
    """Показывает слоты мастера."""
    master = get_master_by_telegram_id(message.from_user.id)
    if not master:
        await message.answer("⛔ Вы не зарегистрированы как мастер.")
        return
    
    slots = get_master_slots(master['id'])
    if not slots:
        await message.answer("📅 У вас нет добавленных слотов.")
        return
    
    text = "📅 **Ваши слоты:**\n\n"
    for s in slots[:20]:
        status = "🟢" if s['is_available'] else "🔴"
        text += f"{status} {s['date']} {s['time']}"
        if s['booking_id']:
            text += " 📌 (занято)"
        text += "\n"
    
    await message.answer(text, parse_mode="Markdown")


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
    """Получает время для слота и сохраняет его."""
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
        
        add_slot(master['id'], date_str, time_str)
        
        await message.answer(
            f"✅ Слот добавлен!\n"
            f"📅 {date_str}\n"
            f"🕐 {time_str}",
            parse_mode="Markdown"
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте **ЧЧ:ММ**", parse_mode="Markdown")