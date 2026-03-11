"""Конфигурация приложения."""
from pathlib import Path
from datetime import timedelta

BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "dining_room.sqlite3"

SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_DO_NOT_USE_DEFAULT"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)