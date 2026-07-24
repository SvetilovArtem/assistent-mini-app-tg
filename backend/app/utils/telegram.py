from aiogram import Bot
from aiogram.types import Chat

async def get_user_by_username(username: str, bot: Bot) -> Chat | None:
    """
    Получает пользователя Telegram по username.
    Возвращает Chat или None, если пользователь не найден.
    """
    if username.startswith('@'):
        username = username[1:]
    
    try:
        user = await bot.get_chat(f"@{username}")
        return user
    except Exception as e:
        print(f"Ошибка get_chat: {e}")
        return None