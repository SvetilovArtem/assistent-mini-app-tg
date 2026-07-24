import sqlite3
from pathlib import Path
from ..config import config

DB_PATH = config.DB_PATH

def get_connection():
    """Возвращает синхронное соединение с БД."""
    # Создаём папку для БД, если её нет
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)