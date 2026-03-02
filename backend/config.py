"""Конфигурация приложения."""
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# SQLite БД (ЛР: реализация хранения меню)
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "dining_room.sqlite3"
