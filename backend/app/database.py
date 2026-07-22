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
    
    # ============================================================
    # ТАБЛИЦЫ
    # ============================================================
    
    # --- Мастера ---
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
    
    # --- Услуги ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            duration_minutes INTEGER NOT NULL,
            prep_time_minutes INTEGER DEFAULT 5,
            cleanup_time_minutes INTEGER DEFAULT 5,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # --- Связь мастеров и услуг ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS master_services (
            master_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            duration_modifier INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            PRIMARY KEY (master_id, service_id),
            FOREIGN KEY (master_id) REFERENCES masters(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')
    
    # --- Слоты ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            service_id INTEGER,
            is_available INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (master_id) REFERENCES masters(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        )
    ''')
    
    # --- Записи клиентов ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            phone TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            master_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL,
            FOREIGN KEY (service_id) REFERENCES services(id),
            FOREIGN KEY (master_id) REFERENCES masters(id)
        )
    ''')
    
    # --- Администраторы (расширяемая) ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
    ''')
    
    # --- Индексы для скорости ---
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_master_id ON bookings(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_master_id ON slots(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_master_services_master_id ON master_services(master_id)')
    
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


def get_all_masters(active_only: bool = True):
    """Получает всех мастеров."""
    conn = get_connection()
    cur = conn.cursor()
    
    query = 'SELECT id, telegram_id, name, phone, is_active FROM masters'
    if active_only:
        query += ' WHERE is_active = 1'
    query += ' ORDER BY name'
    
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'telegram_id': r[1],
        'name': r[2],
        'phone': r[3],
        'is_active': bool(r[4])
    } for r in rows]


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


def update_master(master_id: int, name: str = None, phone: str = None, is_active: bool = None) -> bool:
    """Обновляет данные мастера."""
    conn = get_connection()
    cur = conn.cursor()
    
    updates = []
    params = []
    if name is not None:
        updates.append('name = ?')
        params.append(name)
    if phone is not None:
        updates.append('phone = ?')
        params.append(phone)
    if is_active is not None:
        updates.append('is_active = ?')
        params.append(1 if is_active else 0)
    
    if not updates:
        conn.close()
        return False
    
    params.append(master_id)
    cur.execute(f'UPDATE masters SET {", ".join(updates)} WHERE id = ?', params)
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ============================================================
# УСЛУГИ
# ============================================================

def create_service(
    name: str,
    duration_minutes: int,
    category: str = None,
    description: str = None,
    prep_time: int = 5,
    cleanup_time: int = 5
) -> int:
    """Создаёт новую услугу."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    cur.execute('''
        INSERT INTO services (
            name, category, description, duration_minutes,
            prep_time_minutes, cleanup_time_minutes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, category, description, duration_minutes,
          prep_time, cleanup_time, now))
    
    service_id = cur.lastrowid
    conn.commit()
    conn.close()
    return service_id


def get_all_services(active_only: bool = True):
    """Получает список всех услуг."""
    conn = get_connection()
    cur = conn.cursor()
    
    query = 'SELECT id, name, category, description, duration_minutes, prep_time_minutes, cleanup_time_minutes, is_active FROM services'
    if active_only:
        query += ' WHERE is_active = 1'
    query += ' ORDER BY sort_order, name'
    
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'name': r[1],
        'category': r[2],
        'description': r[3],
        'duration_minutes': r[4],
        'prep_time_minutes': r[5],
        'cleanup_time_minutes': r[6],
        'is_active': bool(r[7])
    } for r in rows]


def get_master_services(master_id: int):
    """Получает услуги, которые может выполнять мастер."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, s.name, s.duration_minutes, s.prep_time_minutes, s.cleanup_time_minutes,
               IFNULL(ms.duration_modifier, 0) as duration_modifier
        FROM services s
        JOIN master_services ms ON s.id = ms.service_id
        WHERE ms.master_id = ? AND ms.is_active = 1 AND s.is_active = 1
        ORDER BY s.category, s.name
    ''', (master_id,))
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'name': r[1],
        'duration_minutes': r[2] + r[5],
        'prep_time_minutes': r[3],
        'cleanup_time_minutes': r[4]
    } for r in rows]


def assign_service_to_master(master_id: int, service_id: int, duration_modifier: int = 0) -> bool:
    """Назначает услугу мастеру."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    cur.execute('''
        INSERT OR REPLACE INTO master_services (master_id, service_id, duration_modifier, is_active)
        VALUES (?, ?, ?, 1)
    ''', (master_id, service_id, duration_modifier))
    
    success = cur.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_total_time_for_service(service_id: int, master_id: int = None) -> int:
    """
    Возвращает общее время на услугу с учётом:
    - длительности
    - подготовки
    - уборки
    - модификатора мастера (если есть)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    if master_id:
        cur.execute('''
            SELECT 
                s.duration_minutes + IFNULL(s.prep_time_minutes, 0) + IFNULL(s.cleanup_time_minutes, 0) + IFNULL(ms.duration_modifier, 0) as total
            FROM services s
            LEFT JOIN master_services ms ON s.id = ms.service_id AND ms.master_id = ?
            WHERE s.id = ?
        ''', (master_id, service_id))
    else:
        cur.execute('''
            SELECT duration_minutes + IFNULL(prep_time_minutes, 0) + IFNULL(cleanup_time_minutes, 0) as total
            FROM services
            WHERE id = ?
        ''', (service_id,))
    
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


# ============================================================
# СЛОТЫ
# ============================================================

def add_slot(master_id: int, date_str: str, time_str: str, service_id: int = None) -> int:
    """Добавляет слот мастеру."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute('''
        INSERT INTO slots (master_id, date, time, service_id, is_available, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, 1, ?, ?)
    ''', (master_id, date_str, time_str, service_id, now, now))
    slot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return slot_id


def get_available_slots(master_id: int, date_str: str):
    """Возвращает доступные слоты мастера на дату."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT time, service_id
        FROM slots
        WHERE master_id = ? AND date = ? AND is_available = 1 AND is_active = 1
        ORDER BY time
    ''', (master_id, date_str))
    rows = cur.fetchall()
    conn.close()
    return [{'time': r[0], 'service_id': r[1]} for r in rows]


def get_master_slots(master_id: int, date_str: str = None):
    """Возвращает все слоты мастера (на дату или все)."""
    conn = get_connection()
    cur = conn.cursor()
    
    if date_str:
        cur.execute('''
            SELECT id, time, service_id, is_available, is_active,
                   (SELECT id FROM bookings WHERE master_id = ? AND date = ? AND time = slots.time AND status = 'active') as booking_id
            FROM slots
            WHERE master_id = ? AND date = ? AND is_active = 1
            ORDER BY time
        ''', (master_id, date_str, master_id, date_str))
    else:
        cur.execute('''
            SELECT id, date, time, service_id, is_available, is_active,
                   (SELECT id FROM bookings WHERE master_id = ? AND date = slots.date AND time = slots.time AND status = 'active') as booking_id
            FROM slots
            WHERE master_id = ? AND is_active = 1
            ORDER BY date, time
        ''', (master_id, master_id))
    
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        if date_str:
            result.append({
                'id': r[0],
                'time': r[1],
                'service_id': r[2],
                'is_available': bool(r[3]),
                'is_active': bool(r[4]),
                'booking_id': r[5]
            })
        else:
            result.append({
                'id': r[0],
                'date': r[1],
                'time': r[2],
                'service_id': r[3],
                'is_available': bool(r[4]),
                'is_active': bool(r[5]),
                'booking_id': r[6]
            })
    return result


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


def confirm_slot(slot_id: int, master_id: int) -> bool:
    """Подтверждает слот (делает его доступным для клиентов)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE slots SET is_active = 1, updated_at = ?
        WHERE id = ? AND master_id = ? AND is_active = 0
    ''', (datetime.now().isoformat(), slot_id, master_id))
    confirmed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return confirmed


# ============================================================
# ЗАПИСИ
# ============================================================

def create_booking(
    user_id: int,
    username: str,
    phone: str,
    service_id: int,
    master_id: int,
    date_str: str,
    time_str: str
) -> int:
    """Создаёт запись клиента."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    # Проверяем, что слот свободен
    cur.execute('''
        SELECT id FROM slots
        WHERE master_id = ? AND date = ? AND time = ? AND is_available = 1 AND is_active = 1
    ''', (master_id, date_str, time_str))
    
    if not cur.fetchone():
        conn.close()
        raise ValueError("Слот уже занят или недоступен")
    
    # Помечаем слот как занятый
    cur.execute('''
        UPDATE slots SET is_available = 0, updated_at = ?
        WHERE master_id = ? AND date = ? AND time = ? AND is_available = 1
    ''', (now, master_id, date_str, time_str))
    
    # Создаём запись
    cur.execute('''
        INSERT INTO bookings (user_id, username, phone, service_id, master_id, date, time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, phone, service_id, master_id, date_str, time_str, now))
    
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    return booking_id


def get_user_bookings(user_id: int):
    """Возвращает активные записи пользователя."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            b.id, 
            s.name as service_name,
            b.date, 
            b.time, 
            b.status,
            m.name as master_name
        FROM bookings b
        LEFT JOIN services s ON b.service_id = s.id
        LEFT JOIN masters m ON b.master_id = m.id
        WHERE b.user_id = ? AND b.status = 'active'
        ORDER BY b.date DESC
    ''', (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'service_name': r[1],
        'date': r[2],
        'time': r[3],
        'status': r[4],
        'master_name': r[5] or 'Не назначен'
    } for r in rows]


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
    
    # Меняем статус записи
    cur.execute('UPDATE bookings SET status = "cancelled" WHERE id = ? AND user_id = ?', (booking_id, user_id))
    
    # Освобождаем слот
    cur.execute('''
        UPDATE slots SET is_available = 1, updated_at = ?
        WHERE master_id = ? AND date = ? AND time = ?
    ''', (datetime.now().isoformat(), master_id, date_str, time_str))
    
    conn.commit()
    conn.close()
    return True


def get_all_bookings(master_id: int = None, limit: int = 30):
    """Возвращает все записи (опционально для мастера)."""
    conn = get_connection()
    cur = conn.cursor()
    
    if master_id:
        cur.execute('''
            SELECT 
                b.id, b.user_id, b.username, b.phone, 
                s.name as service_name,
                b.date, b.time, b.status, b.created_at,
                m.name as master_name
            FROM bookings b
            LEFT JOIN services s ON b.service_id = s.id
            LEFT JOIN masters m ON b.master_id = m.id
            WHERE b.status = 'active' AND b.master_id = ?
            ORDER BY b.date DESC LIMIT ?
        ''', (master_id, limit))
    else:
        cur.execute('''
            SELECT 
                b.id, b.user_id, b.username, b.phone, 
                s.name as service_name,
                b.date, b.time, b.status, b.created_at,
                m.name as master_name
            FROM bookings b
            LEFT JOIN services s ON b.service_id = s.id
            LEFT JOIN masters m ON b.master_id = m.id
            WHERE b.status = 'active'
            ORDER BY b.date DESC LIMIT ?
        ''', (limit,))
    
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'user_id': r[1],
        'username': r[2],
        'phone': r[3],
        'service_name': r[4] or 'Не указана',
        'date': r[5],
        'time': r[6],
        'status': r[7],
        'created_at': r[8],
        'master_name': r[9] or 'Не назначен'
    } for r in rows]


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
    return {
        'total': total,
        'active': active,
        'cancelled': cancelled,
        'today': today_count
    }


# ============================================================
# АДМИНЫ
# ============================================================

def get_admin_by_telegram_id(telegram_id: int):
    """Получает администратора по Telegram ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, role FROM admins WHERE telegram_id = ?', (telegram_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'role': row[2]}
    return None


def add_admin(telegram_id: int, name: str, role: str = 'admin') -> int:
    """Добавляет нового администратора."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute('''
        INSERT INTO admins (telegram_id, name, role, created_at)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, name, role, now))
    admin_id = cur.lastrowid
    conn.commit()
    conn.close()
    return admin_id