import logging
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..config import config
from ..db import (
    get_all_services,
    get_all_masters,
    get_master_services,
    get_available_slots,
    create_booking,
    get_user_bookings,
    cancel_booking,
    get_master_by_id
)
from ..keyboards.client import client_menu

router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# FSM ДЛЯ ЗАПИСИ
# ============================================================

class BookingStates(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    phone = State()


# ============================================================
# КНОПКА "❓ О НАС"
# ============================================================

@router.message(F.text == "❓ О нас")
async def about(message: types.Message):
    """Информация о салоне."""
    await message.answer(
        f"✂️ **Салон красоты «{config.SALON_NAME}»**\n\n"
        f"📍 {config.SALON_ADDRESS}\n"
        f"🕐 {config.SALON_WORK_HOURS}\n"
        f"📞 {config.SALON_PHONE}\n\n"
        "💇‍♂️ Мы работаем с 2015 года. В нашей команде — профессиональные мастера с опытом от 5 лет.\n"
        "Используем только премиальную косметику и стерильные инструменты.\n\n"
        "Записаться можно прямо сейчас — нажмите ✂️ Записаться!",
        parse_mode="Markdown"
    )


# ============================================================
# КНОПКА "📞 КОНТАКТЫ"
# ============================================================

@router.message(F.text == "📞 Контакты")
async def contacts(message: types.Message):
    """Контактные данные."""
    await message.answer(
        f"📞 **Телефон**: {config.SALON_PHONE}\n"
        f"📍 **Адрес**: {config.SALON_ADDRESS}\n"
        f"🕐 **Часы работы**: {config.SALON_WORK_HOURS}\n\n"
        "📷 Instagram: @salon_lokon\n"
        "📱 Telegram: @salon_lokon_chat",
        parse_mode="Markdown"
    )


# ============================================================
# КНОПКА "✂️ ЗАПИСАТЬСЯ" — ШАГ 1: УСЛУГА
# ============================================================

@router.message(F.text == "✂️ Записаться")
async def start_booking(message: types.Message, state: FSMContext):
    """Начинает процесс записи: показывает список услуг."""
    services = get_all_services(active_only=True)
    if not services:
        await message.answer("😔 К сожалению, услуги временно недоступны. Попробуйте позже.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s['name'], callback_data=f"service_{s['id']}")]
        for s in services
    ])
    
    await state.set_state(BookingStates.service)
    await message.answer(
        "✂️ **Выберите услугу:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ============================================================
# ШАГ 2: ВЫБОР МАСТЕРА
# ============================================================

@router.callback_query(BookingStates.service)
async def select_service(callback: types.CallbackQuery, state: FSMContext):
    """Показывает мастеров, которые оказывают выбранную услугу."""
    service_id = int(callback.data.replace("service_", ""))
    await state.update_data(service_id=service_id)
    
    masters = get_all_masters(active_only=True)
    available_masters = []
    for m in masters:
        master_services = get_master_services(m['id'])
        if any(s['id'] == service_id for s in master_services):
            available_masters.append(m)
    
    if not available_masters:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет мастеров для этой услуги.\n"
            "Пожалуйста, выберите другую услугу.",
        )
        await state.clear()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m['name'], callback_data=f"master_{m['id']}")]
        for m in available_masters
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_services")])
    
    await state.set_state(BookingStates.master)
    await callback.message.edit_text(
        "💇 **Выберите мастера:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_services")
async def back_to_services(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору услуги."""
    await start_booking(callback.message, state)
    await callback.answer()


# ============================================================
# ШАГ 3: ВЫБОР ДАТЫ
# ============================================================

@router.callback_query(BookingStates.master)
async def select_master(callback: types.CallbackQuery, state: FSMContext):
    """Показывает даты для выбранного мастера."""
    if callback.data == "back_to_services":
        await start_booking(callback.message, state)
        await callback.answer()
        return
    
    master_id = int(callback.data.replace("master_", ""))
    await state.update_data(master_id=master_id)
    
    # Показываем следующие 7 дней
    dates = []
    for i in range(7):
        d = datetime.now() + timedelta(days=i)
        dates.append(d.strftime("%d.%m.%Y"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"date_{d}")]
        for d in dates
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_masters")])
    
    await state.set_state(BookingStates.date)
    await callback.message.edit_text(
        "📅 **Выберите дату:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_masters")
async def back_to_masters(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору мастера."""
    data = await state.get_data()
    service_id = data.get('service_id')
    
    masters = get_all_masters(active_only=True)
    available_masters = []
    for m in masters:
        master_services = get_master_services(m['id'])
        if any(s['id'] == service_id for s in master_services):
            available_masters.append(m)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m['name'], callback_data=f"master_{m['id']}")]
        for m in available_masters
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_services")])
    
    await state.set_state(BookingStates.master)
    await callback.message.edit_text(
        "💇 **Выберите мастера:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ШАГ 4: ВЫБОР ВРЕМЕНИ
# ============================================================

@router.callback_query(BookingStates.date)
async def select_date(callback: types.CallbackQuery, state: FSMContext):
    """Показывает доступное время для выбранной даты."""
    if callback.data == "back_to_masters":
        await back_to_masters(callback, state)
        return
    
    date_str = callback.data.replace("date_", "")
    await state.update_data(date=date_str)
    
    data = await state.get_data()
    master_id = data.get('master_id')
    slots = get_available_slots(master_id, date_str)
    
    if not slots:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Выбрать другую дату", callback_data="back_to_dates")]
        ])
        await callback.message.edit_text(
            f"😔 На {date_str} нет свободных слотов.\n"
            f"Пожалуйста, выберите другую дату.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s['time'], callback_data=f"time_{s['time']}")]
        for s in slots
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_dates")])
    
    await state.set_state(BookingStates.time)
    await callback.message.edit_text(
        f"📅 Дата: **{date_str}**\n\n"
        f"🕐 **Выберите время:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_dates")
async def back_to_dates(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору даты."""
    dates = []
    for i in range(7):
        d = datetime.now() + timedelta(days=i)
        dates.append(d.strftime("%d.%m.%Y"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d, callback_data=f"date_{d}")]
        for d in dates
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_masters")])
    
    await state.set_state(BookingStates.date)
    await callback.message.edit_text(
        "📅 **Выберите дату:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ШАГ 5: ВВОД ТЕЛЕФОНА
# ============================================================

@router.callback_query(BookingStates.time)
async def select_time(callback: types.CallbackQuery, state: FSMContext):
    """Сохраняет время и запрашивает телефон."""
    if callback.data == "back_to_dates":
        await back_to_dates(callback, state)
        return
    
    time_str = callback.data.replace("time_", "")
    await state.update_data(time=time_str)
    
    await state.set_state(BookingStates.phone)
    await callback.message.edit_text(
        "📱 **Введите ваш номер телефона:**\n"
        "Например: +7 999 123-45-67\n\n"
        "Или нажмите «❌ Отмена» чтобы прервать запись.",
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================================
# ШАГ 6: ПОДТВЕРЖДЕНИЕ И СОХРАНЕНИЕ
# ============================================================

@router.message(BookingStates.phone)
async def enter_phone(message: types.Message, state: FSMContext):
    """Сохраняет телефон и показывает подтверждение."""
    phone = message.text.strip()
    if len(phone) < 9:
        await message.answer(
            "❌ Слишком короткий номер. Введите полный номер телефона:\n"
            "Пример: +7 999 123-45-67"
        )
        return
    
    await state.update_data(phone=phone)
    
    data = await state.get_data()
    service_id = data.get('service_id')
    master_id = data.get('master_id')
    date_str = data.get('date')
    time_str = data.get('time')
    
    # Получаем названия для красивого вывода
    services = get_all_services(active_only=True)
    service_name = next((s['name'] for s in services if s['id'] == service_id), "Неизвестно")
    
    masters = get_all_masters(active_only=True)
    master_name = next((m['name'] for m in masters if m['id'] == master_id), "Неизвестно")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")]
    ])
    
    await message.answer(
        f"📝 **Проверьте данные записи:**\n\n"
        f"✂️ Услуга: {service_name}\n"
        f"💇 Мастер: {master_name}\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Всё верно?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_"))
async def confirm_booking(callback: types.CallbackQuery, state: FSMContext):
    """Создаёт запись или отменяет."""
    if callback.data == "confirm_no":
        await state.clear()
        await callback.message.edit_text(
            "❌ Запись отменена. Если передумаете — нажмите ✂️ Записаться."
        )
        await callback.answer()
        return
    
    data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username or "Не указан"
    service_id = data.get('service_id')
    master_id = data.get('master_id')
    date_str = data.get('date')
    time_str = data.get('time')
    phone = data.get('phone')
    
    # Получаем названия для красивого вывода
    services = get_all_services(active_only=True)
    service_name = next((s['name'] for s in services if s['id'] == service_id), "Неизвестно")
    
    masters = get_all_masters(active_only=True)
    master_name = next((m['name'] for m in masters if m['id'] == master_id), "Неизвестно")  # <-- ВОТ ЭТО БЫЛО ПРОПУЩЕНО
    
    try:
        booking_id = create_booking(
            user_id=user_id,
            username=username,
            phone=phone,
            service_id=service_id,
            master_id=master_id,
            date_str=date_str,
            time_str=time_str
        )
        
        await callback.message.edit_text(
            f"✅ **Вы успешно записаны!**\n\n"
            f"✂️ Услуга: {service_name}\n"
            f"💇 Мастер: {master_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n"
            f"📱 Телефон: {phone}\n\n"
            f"📍 {config.SALON_ADDRESS}\n"
            f"📞 {config.SALON_PHONE}\n\n"
            f"🆔 Номер записи: #{booking_id}\n\n"
            f"Ждём вас! 🥰",
            parse_mode="Markdown"
        )
        
        # Уведомляем мастера (если у него есть Telegram ID)
        master = get_master_by_id(master_id)
        if master and master.get('telegram_id'):
            try:
                await callback.bot.send_message(
                    master['telegram_id'],
                    f"🆕 **Новая запись!**\n\n"
                    f"👤 Клиент: @{username}\n"
                    f"✂️ Услуга: {service_name}\n"
                    f"📅 Дата: {date_str}\n"
                    f"🕐 Время: {time_str}\n"
                    f"📱 Телефон: {phone}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить мастера: {e}")
        
        await state.clear()
        
    except ValueError as e:
        await callback.message.edit_text(f"❌ {str(e)}\n\nПожалуйста, попробуйте записаться заново.")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка создания записи: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при создании записи.\nПожалуйста, попробуйте позже.")
        await state.clear()
    
    await callback.answer()
    """Создаёт запись или отменяет."""
    if callback.data == "confirm_no":
        await state.clear()
        await callback.message.edit_text(
            "❌ Запись отменена. Если передумаете — нажмите ✂️ Записаться."
        )
        await callback.answer()
        return
    
    data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username or "Не указан"
    service_id = data.get('service_id')
    master_id = data.get('master_id')
    date_str = data.get('date')
    time_str = data.get('time')
    phone = data.get('phone')
    
    try:
        booking_id = create_booking(
            user_id=user_id,
            username=username,
            phone=phone,
            service_id=service_id,
            master_id=master_id,
            date_str=date_str,
            time_str=time_str
        )
        
        services = get_all_services(active_only=True)
        service_name = next((s['name'] for s in services if s['id'] == service_id), "Неизвестно")
        
        await callback.message.edit_text(
            f"✅ **Вы успешно записаны!**\n\n"
            f"✂️ Услуга: {service_name}\n"
            f"💇 Мастер: {master_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n"
            f"📱 Телефон: {phone}\n\n"
            f"📍 {config.SALON_ADDRESS}\n"
            f"📞 {config.SALON_PHONE}\n\n"
            f"🆔 Номер записи: #{booking_id}\n\n"
            f"Ждём вас! 🥰",
            parse_mode="Markdown"
        )
        
        # Уведомляем мастера (если у него есть Telegram ID)
        master = get_master_by_id(master_id)
        if master and master.get('telegram_id'):
            try:
                await callback.bot.send_message(
                    master['telegram_id'],
                    f"🆕 **Новая запись!**\n\n"
                    f"👤 Клиент: @{username}\n"
                    f"✂️ Услуга: {service_name}\n"
                    f"📅 Дата: {date_str}\n"
                    f"🕐 Время: {time_str}\n"
                    f"📱 Телефон: {phone}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить мастера: {e}")
        
        await state.clear()
        
    except ValueError as e:
        await callback.message.edit_text(f"❌ {str(e)}\n\nПожалуйста, попробуйте записаться заново.")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка создания записи: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при создании записи.\nПожалуйста, попробуйте позже.")
        await state.clear()
    
    await callback.answer()


# ============================================================
# КНОПКА "📋 МОИ ЗАПИСИ"
# ============================================================

@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: types.Message):
    """Показывает все записи клиента."""
    bookings = get_user_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer(
            "🔍 У вас пока нет активных записей.\n"
            "Хотите записаться? Нажмите ✂️ Записаться!"
        )
        return
    
    text = "📋 **Ваши записи:**\n\n"
    for b in bookings:
        text += (
            f"🆔 #{b['id']}\n"
            f"✂️ {b['service_name']}\n"
            f"💇 {b['master_name']}\n"
            f"📅 {b['date']} в {b['time']}\n"
            f"📌 {b['status']}\n\n"
        )
    
    # Кнопка для отмены последней записи
    last_id = bookings[0]['id']
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить последнюю запись", callback_data=f"cancel_{last_id}")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(lambda c: c.data and c.data.startswith("cancel_"))
async def cancel_booking_callback(callback: types.CallbackQuery):
    """Отменяет запись."""
    booking_id = int(callback.data.replace("cancel_", ""))
    user_id = callback.from_user.id
    
    if cancel_booking(booking_id, user_id):
        await callback.message.edit_text(
            "✅ Запись успешно отменена!",
            reply_markup=None
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось отменить запись. Возможно, она уже была отменена.",
            reply_markup=None
        )
    await callback.answer()