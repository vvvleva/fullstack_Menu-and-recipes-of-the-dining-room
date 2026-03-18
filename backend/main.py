"""Точка входа приложения - запуск backend и frontend серверов."""
import sys
import threading
import uvicorn
import subprocess
import os
import time
import webbrowser
from pathlib import Path

# Добавляем путь к backend в sys.path
sys.path.insert(0, str(Path(__file__).parent))
from app import app

def run_frontend():
    """Запуск фронтенд сервера."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    if not frontend_dir.exists():
        print("ОШИБКА: Папка frontend не найдена!")
        print(f"Искал здесь: {frontend_dir}")
        print("Создайте папку frontend рядом с backend")
        return
    
    # Проверяем наличие основных файлов
    html_file = frontend_dir / "index.html"
    if not html_file.exists():
        print(f"ОШИБКА: Файл index.html не найден в {frontend_dir}")
        return
    
    os.chdir(str(frontend_dir))
    print(f"Фронтенд сервер запускается в {frontend_dir}")
    print("Сервер доступен по адресу: http://localhost:3000")
    
    try:
        # Запускаем сервер
        subprocess.run([sys.executable, "-m", "http.server", "3000"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска сервера: {e}")
    except KeyboardInterrupt:
        print("Фронтенд сервер остановлен")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

def open_browser_delayed():
    """Открыть браузер через 2 секунды."""
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:3000")
        print("Браузер открыт по адресу http://localhost:3000")
    except Exception as e:
        print(f"Не удалось открыть браузер: {e}")

def check_files():
    """Проверка наличия файлов."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    if not frontend_dir.exists():
        print(f"Папка frontend не существует по пути: {frontend_dir}")
        return False
    
    required = ["index.html", "script.js", "style.css", "register.html", "register.js"]
    missing = []
    
    for file in required:
        if not (frontend_dir / file).exists():
            missing.append(file)
    
    if missing:
        print(f"Отсутствуют файлы в {frontend_dir}: {', '.join(missing)}")
        return False
    
    print("Все необходимые файлы найдены")
    return True

def print_startup_info(files_ok):
    """Вывод информации при запуске."""
    print("\n" + "=" * 60)
    print("ЗАПУСК ПРИЛОЖЕНИЯ СТОЛОВАЯ #2049".center(60))
    print("=" * 60)
    
    if files_ok:
        print(" Фронтенд сервер: http://localhost:3000")
        print("   Статус: будет запущен")
    else:
        print(" Фронтенд сервер: НЕ БУДЕТ ЗАПУЩЕН")
        print("   Причина: отсутствуют файлы")
    
    print(" Бэкенд сервер: http://localhost:8000")
    print(" Документация API: http://localhost:8000/docs")
    print("=" * 60)
    print(" Нажмите Ctrl+C для остановки всех сервисов")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    # Проверяем наличие файлов
    files_ok = check_files()
    print_startup_info(files_ok)
    
    # Запускаем фронтенд если файлы есть
    if files_ok:
        # Запускаем фронтенд сервер в отдельном потоке
        frontend_thread = threading.Thread(target=run_frontend, daemon=True)
        frontend_thread.start()
        
        # Открываем браузер через 2 секунды
        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()
    else:
        print("Продолжаем запуск только бэкенд сервера...")
    
    # Запускаем бэкенд
    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nОстановка приложения...")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка запуска бэкенда: {e}")
        sys.exit(1)