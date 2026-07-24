import sqlite3
from .connection import get_connection

def init_db():
    """Создаёт все таблицы, если их нет."""
    conn = get_connection()
    cur = conn.cursor()
    
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
    
    # --- Записи ---
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
    
    # --- Администраторы ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
    ''')
    
    # --- Индексы ---
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_master_id ON bookings(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_master_id ON slots(master_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_master_services_master_id ON master_services(master_id)')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")