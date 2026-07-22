import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Настройки приложения."""
    
    # --- Telegram Bot ---
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = [
        int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()
    ]
    
    # --- База данных ---
    DB_PATH: str = os.getenv("DB_PATH", "data/bookings.db")
    
    # --- Данные салона ---
    SALON_NAME: str = os.getenv("SALON_NAME", "Салон красоты")
    SALON_ADDRESS: str = os.getenv("SALON_ADDRESS", "Адрес не указан")
    SALON_PHONE: str = os.getenv("SALON_PHONE", "Телефон не указан")
    SALON_WORK_HOURS: str = os.getenv("SALON_WORK_HOURS", "10:00 - 20:00")
    
    # --- URL для Mini App ---
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "http://localhost:5173")
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    
    @classmethod
    def ensure_dirs(cls) -> None:
        """Создаёт необходимые папки."""
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет, что все обязательные настройки заданы."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан! Проверьте .env файл.")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не задан! Укажите хотя бы один Telegram ID.")
        return True


config = Config()