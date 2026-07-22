import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..config import config
from ..database import get_master_by_telegram_id, get_master_slots

router = Router()
logger = logging.getLogger(__name__)


class BookingStates(StatesGroup):
    """Состояния для записи клиента."""
    service = State()
    master = State()
    phone = State()
    date = State()
    time = State()


@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: types.Message):
    """Показывает записи клиента."""
    await message.answer("📋 Ваши записи будут здесь...")