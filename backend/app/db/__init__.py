from .connection import get_connection
from .models import init_db
from .queries import (
 
    get_master_by_telegram_id,
    get_master_by_id,
    get_all_masters,
    create_master,

    get_all_services,
    get_master_services,
    assign_service_to_master,

    add_slot,
    get_available_slots,
    get_master_slots,
    toggle_slot_availability,  
    delete_slot,

    create_booking,
    get_user_bookings,
    get_all_bookings,
    cancel_booking,
    get_statistics,
)