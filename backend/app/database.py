import sqlite3
from datetime import datetime
from .config import config


def get_connection():
    """Возвращает соединение с БД."""
    return sqlite3.connect(config.DB_PATH)


def init_db():
    """Создаёт все таблицы, если их нет."""
    conn = get_connection()
    cur = conn.cursor()
    
    # --- Таблица мастеров ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''')
    
    # --- Таблица слотов ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_available INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (master_id) REFERENCES masters(id)
        )
    ''')
    
    # --- Таблица записей ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            master_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            FOREIGN KEY (master_id) REFERENCES masters(id)
        )
    ''')
    
    # --- Индексы для скорости ---
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_master_id ON bookings(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_master_id ON slots(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date)')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


# ============================================================
# МАСТЕРА
# ============================================================

def get_master_by_telegram_id(telegram_id: int):
    """Получает мастера по Telegram ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, phone, is_active FROM masters WHERE telegram_id = ?', (telegram_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'phone': row[2], 'is_active': bool(row[3])}
    return None


def get_all_masters():
    """Получает всех активных мастеров."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, telegram_id, name FROM masters WHERE is_active = 1')
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'telegram_id': r[1], 'name': r[2]} for r in rows]


def create_master(telegram_id: int, name: str, phone: str = None) -> int:
    """Создаёт нового мастера."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute('''
        INSERT INTO masters (telegram_id, name, phone, created_at)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, name, phone, now))
    master_id = cur.lastrowid
    conn.commit()
    conn.close()
    return master_id


# ============================================================
# СЛОТЫ
# ============================================================

def add_slot(master_id: int, date_str: str, time_str: str) -> int:
    """Добавляет слот мастеру."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute('''
        INSERT INTO slots (master_id, date, time, is_available, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 1, 1, ?, ?)
    ''', (master_id, date_str, time_str, now, now))
    slot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return slot_id


def get_available_slots(master_id: int, date_str: str):
    """Возвращает доступные слоты мастера на дату."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT time FROM slots
        WHERE master_id = ? AND date = ? AND is_available = 1 AND is_active = 1
        ORDER BY time
    ''', (master_id, date_str))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_master_slots(master_id: int, date_str: str = None):
    """Возвращает все слоты мастера (на дату или все)."""
    conn = get_connection()
    cur = conn.cursor()
    
    if date_str:
        cur.execute('''
            SELECT id, time, is_available, is_active,
                   (SELECT id FROM bookings WHERE master_id = ? AND date = ? AND time = slots.time AND status = 'active') as booking_id
            FROM slots
            WHERE master_id = ? AND date = ? AND is_active = 1
            ORDER BY time
        ''', (master_id, date_str, master_id, date_str))
    else:
        cur.execute('''
            SELECT id, date, time, is_available, is_active,
                   (SELECT id FROM bookings WHERE master_id = ? AND date = slots.date AND time = slots.time AND status = 'active') as booking_id
            FROM slots
            WHERE master_id = ? AND is_active = 1
            ORDER BY date, time
        ''', (master_id, master_id))
    
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'time': r[1] if date_str else r[1], 'is_available': bool(r[2]), 'is_active': bool(r[3]), 'booking_id': r[4]} for r in rows]


def toggle_slot_availability(slot_id: int, master_id: int) -> bool:
    """Включает/выключает доступность слота."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT is_available FROM slots WHERE id = ? AND master_id = ?', (slot_id, master_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    new_status = 0 if row[0] else 1
    cur.execute('UPDATE slots SET is_available = ?, updated_at = ? WHERE id = ? AND master_id = ?',
                (new_status, datetime.now().isoformat(), slot_id, master_id))
    conn.commit()
    conn.close()
    return True


def delete_slot(slot_id: int, master_id: int) -> bool:
    """Удаляет слот (если на него нет записей)."""
    conn = get_connection()
    cur = conn.cursor()
    # Проверяем, есть ли запись на этот слот
    cur.execute('''
        SELECT id FROM bookings 
        WHERE master_id = ? AND date = (SELECT date FROM slots WHERE id = ?) 
        AND time = (SELECT time FROM slots WHERE id = ?) AND status = 'active'
    ''', (master_id, slot_id, slot_id))
    if cur.fetchone():
        conn.close()
        return False
    cur.execute('UPDATE slots SET is_active = 0, updated_at = ? WHERE id = ? AND master_id = ?',
                (datetime.now().isoformat(), slot_id, master_id))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ============================================================
# ЗАПИСИ
# ============================================================

def create_booking(user_id: int, username: str, phone: str, service: str,
                   master_id: int, date_str: str, time_str: str) -> int:
    """Создаёт запись клиента."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    # Помечаем слот как занятый
    cur.execute('''
        UPDATE slots SET is_available = 0, updated_at = ?
        WHERE master_id = ? AND date = ? AND time = ? AND is_available = 1
    ''', (now, master_id, date_str, time_str))
    
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Слот уже занят или недоступен")
    
    cur.execute('''
        INSERT INTO bookings (user_id, username, phone, service, master_id, date, time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, phone, service, master_id, date_str, time_str, now))
    
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    return booking_id


def get_user_bookings(user_id: int):
    """Возвращает записи пользователя."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT b.id, b.service, b.date, b.time, b.status, m.name as master_name
        FROM bookings b
        LEFT JOIN masters m ON b.master_id = m.id
        WHERE b.user_id = ? AND b.status = 'active'
        ORDER BY b.date DESC
    ''', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'service': r[1], 'date': r[2], 'time': r[3], 'status': r[4], 'master_name': r[5]} for r in rows]


def cancel_booking(booking_id: int, user_id: int) -> bool:
    """Отменяет запись и освобождает слот."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT master_id, date, time FROM bookings WHERE id = ? AND user_id = ?', (booking_id, user_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    
    master_id, date_str, time_str = row
    cur.execute('UPDATE bookings SET status = "cancelled" WHERE id = ? AND user_id = ?', (booking_id, user_id))
    cur.execute('UPDATE slots SET is_available = 1, updated_at = ? WHERE master_id = ? AND date = ? AND time = ?',
                (datetime.now().isoformat(), master_id, date_str, time_str))
    conn.commit()
    conn.close()
    return True


def get_all_bookings(master_id: int = None, limit: int = 30):
    """Возвращает все записи (опционально для мастера)."""
    conn = get_connection()
    cur = conn.cursor()
    
    if master_id:
        cur.execute('''
            SELECT b.id, b.user_id, b.username, b.phone, b.service, b.date, b.time, b.status, b.created_at, m.name as master_name
            FROM bookings b
            LEFT JOIN masters m ON b.master_id = m.id
            WHERE b.status = 'active' AND b.master_id = ?
            ORDER BY b.date DESC LIMIT ?
        ''', (master_id, limit))
    else:
        cur.execute('''
            SELECT b.id, b.user_id, b.username, b.phone, b.service, b.date, b.time, b.status, b.created_at, m.name as master_name
            FROM bookings b
            LEFT JOIN masters m ON b.master_id = m.id
            WHERE b.status = 'active'
            ORDER BY b.date DESC LIMIT ?
        ''', (limit,))
    
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'user_id': r[1], 'username': r[2], 'phone': r[3], 'service': r[4],
             'date': r[5], 'time': r[6], 'status': r[7], 'created_at': r[8], 'master_name': r[9] or 'Не назначен'} for r in rows]


def get_statistics(master_id: int = None):
    """Возвращает статистику по записям."""
    conn = get_connection()
    cur = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if master_id:
        cur.execute('SELECT COUNT(*) FROM bookings WHERE master_id = ?', (master_id,))
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE master_id = ? AND status = "active"', (master_id,))
        active = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE master_id = ? AND status = "cancelled"', (master_id,))
        cancelled = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE master_id = ? AND date = ? AND status = "active"', (master_id, today))
        today_count = cur.fetchone()[0]
    else:
        cur.execute('SELECT COUNT(*) FROM bookings')
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE status = "active"')
        active = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE status = "cancelled"')
        cancelled = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM bookings WHERE date = ? AND status = "active"', (today,))
        today_count = cur.fetchone()[0]
    
    conn.close()
    return {'total': total, 'active': active, 'cancelled': cancelled, 'today': today_count}