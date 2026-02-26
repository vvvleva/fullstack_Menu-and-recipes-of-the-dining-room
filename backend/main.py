from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import uvicorn
import os
import threading
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from routes.menu import router as menu_router

# Создаем приложение
app = FastAPI(
    title="Столовая #2049 API",
    description="API для столовой с AI-анализом аллергенов",
    version="1.0.0"
)

# Настройка CORS - позволяет фронтенду с других доменов обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем пути
BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# Монтируем статические файлы фронтенда 
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    @app.get("/frontend")
    @app.get("/frontend/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        """Отдача фронтенда через FastAPI"""
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend files not found"}

# Подключаем маршруты меню и AI‑анализа (ЛР №2, подготовка к ЛР №4–7)
app.include_router(menu_router)


# Корневой эндпоинт
@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API Столовой #2049",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "menu": "/api/menu",
            "health": "/health",
            "frontend": "/frontend"
        }
    }

# Эндпоинт для проверки здоровья
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "Столовая #2049 API"
    }

def run_frontend_server():
    """Запуск простого HTTP сервера для фронтенда"""
    if not FRONTEND_DIR.exists():
        print(f"Папка фронтенда не найдена: {FRONTEND_DIR}")
        return
    
    os.chdir(str(FRONTEND_DIR))
    print(f"Запуск фронтенд сервера в {FRONTEND_DIR}")
    
    if sys.platform == "win32":
        # Для Windows используем Python HTTP сервер
        subprocess.run([sys.executable, "-m", "http.server", "3000"])
    else:
        subprocess.run([sys.executable, "-m", "http.server", "3000"])

def open_browser_later():
    """Открыть браузер через 2 секунды"""
    time.sleep(2)
    webbrowser.open("http://localhost:3000")

def check_frontend_files():
    """Проверка наличия файлов фронтенда"""
    if not FRONTEND_DIR.exists():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Папка фронтенда не найдена по пути {FRONTEND_DIR}")
        print("Создайте папку frontend и добавьте в неё index.html, style.css, script.js")
        return False
    
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Файл index.html не найден в {FRONTEND_DIR}")
        return False
    
    return True

# Запуск сервера
if __name__ == "__main__":
    print("=" * 50)
    print("ЗАПУСК ПРИЛОЖЕНИЯ СТОЛОВАЯ #2049")
    print("=" * 50)
    
    # Проверяем наличие файлов фронтенда
    frontend_ok = check_frontend_files()
    
    if frontend_ok:
        # Запускаем фронтенд сервер в отдельном потоке
        frontend_thread = threading.Thread(target=run_frontend_server, daemon=True)
        frontend_thread.start()
        
        # Открываем браузер
        browser_thread = threading.Thread(target=open_browser_later, daemon=True)
        browser_thread.start()
        
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
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nОстановка приложения...")
        sys.exit(0)