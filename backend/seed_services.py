from app.db import create_service
from app.db.models import init_db

init_db()

services = [
    {"name": "💇 Мужская стрижка", "duration": 60, "category": "Стрижки"},
    {"name": "💆 Женская стрижка", "duration": 90, "category": "Стрижки"},
    {"name": "🎨 Окрашивание", "duration": 90, "category": "Окрашивание"},
    {"name": "🌿 Уход за волосами", "duration": 30, "category": "Уход"},
    {"name": "📋 Другое", "duration": 30, "category": "Прочее"},
]

for s in services:
    create_service(
        name=s["name"],
        duration_minutes=s["duration"],
        category=s["category"]
    )
    print(f"✅ Добавлена услуга: {s['name']} ({s['duration']} мин)")