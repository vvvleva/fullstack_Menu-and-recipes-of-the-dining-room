"""Запуск сервера и вспомогательные функции."""
import os
import subprocess
import sys
import threading
import time
import webbrowser

from config import FRONTEND_DIR, PROJECT_DIR


def run_frontend_server() -> None:
    """Запуск простого HTTP сервера для фронтенда."""
    if not FRONTEND_DIR.exists():
        print(f"Папка фронтенда не найдена: {FRONTEND_DIR}")
        return

    os.chdir(str(FRONTEND_DIR))
    print(f"Запуск фронтенд сервера в {FRONTEND_DIR}")

    if sys.platform == "win32":
        subprocess.run([sys.executable, "-m", "http.server", "3000"])
    else:
        subprocess.run([sys.executable, "-m", "http.server", "3000"])


def open_browser_later() -> None:
    """Открыть браузер через 2 секунды."""
    time.sleep(2)
    webbrowser.open("http://localhost:3000")


def check_frontend_files() -> bool:
    """Проверка наличия файлов фронтенда."""
    if not FRONTEND_DIR.exists():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Папка фронтенда не найдена по пути {FRONTEND_DIR}")
        print("Создайте папку frontend и добавьте в неё index.html, style.css, script.js")
        return False

    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Файл index.html не найден в {FRONTEND_DIR}")
        return False

    return True


def print_startup_info(frontend_ok: bool) -> None:
    """Вывод информации при запуске."""
    print("=" * 50)
    print("ЗАПУСК ПРИЛОЖЕНИЯ СТОЛОВАЯ #2049")

    if frontend_ok:
        print("Фронтенд сервер запускается на http://localhost:3000")
    else:
        print("Фронтенд не будет запущен из-за отсутствия файлов")
        print(f"Ожидается структура: {PROJECT_DIR}")
        print("  - backend/main.py")
        print("  - frontend/index.html")
        print("  - frontend/style.css")
        print("  - frontend/script.js")

    print("Запуск бэкенд сервера...")
    print("Бэкенд API: http://localhost:8000")
    print("Документация API: http://localhost:8000/docs")
    if frontend_ok:
        print("Фронтенд (альтернативный): http://localhost:8000/frontend")
    print("\nНажмите Ctrl+C для остановки всех сервисов")