"""Конфигурация приложения."""
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
