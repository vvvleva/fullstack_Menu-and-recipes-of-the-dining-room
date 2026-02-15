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

# Создаем приложение
app = FastAPI(
    title="Столовая #2049 API",
    description="API для столовой с AI-анализом аллергенов",
    version="1.0.0"
)

# Настройка CORS
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

# Монтируем статические файлы фронтенда (если папка существует)
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

# База данных в памяти
menu_items = [
    {
        "id": 1,
        "name": "Цезарь с курицей",
        "price": 350,
        "weight": 250,
        "category": "салаты",
        "ingredients": ["курица", "салат айсберг", "соус", "пармезан", "грецкий орех", "гренки"],
        "allergens": ["орехи", "глютен", "лактоза"],
        "calories": 420,
        "available": True
    },
    {
        "id": 2,
        "name": "Греческий салат",
        "price": 300,
        "weight": 200,
        "category": "салаты",
        "ingredients": ["помидоры", "огурцы", "фета", "оливки", "оливковое масло"],
        "allergens": ["лактоза"],
        "calories": 250,
        "available": True
    },
    {
        "id": 3,
        "name": "Борщ",
        "price": 280,
        "weight": 300,
        "category": "супы",
        "ingredients": ["свекла", "капуста", "картофель", "говядина", "сметана"],
        "allergens": ["лактоза"],
        "calories": 180,
        "available": True
    },
    {
        "id": 4,
        "name": "Котлеты с пюре",
        "price": 380,
        "weight": 350,
        "category": "горячее",
        "ingredients": ["котлеты", "картофельное пюре", "соус"],
        "allergens": ["глютен", "лактоза"],
        "calories": 550,
        "available": True
    }
]

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

# Получение всего меню
@app.get("/api/menu")
async def get_menu():
    return {
        "status": "success",
        "data": menu_items,
        "count": len(menu_items)
    }

# Получение конкретного блюда
@app.get("/api/menu/{item_id}")
async def get_menu_item(item_id: int):
    for item in menu_items:
        if item["id"] == item_id:
            return {
                "status": "success",
                "data": item
            }
    return {
        "status": "error",
        "message": "Блюдо не найдено"
    }

# Получение блюд по категории
@app.get("/api/menu/category/{category}")
async def get_menu_by_category(category: str):
    filtered = [item for item in menu_items if item["category"] == category and item["available"]]
    return {
        "status": "success",
        "category": category,
        "data": filtered,
        "count": len(filtered)
    }

# AI-анализ аллергенов
@app.get("/api/analyze/{item_id}/{user_allergens}")
async def analyze_allergens(item_id: int, user_allergens: str):
    dish = None
    for item in menu_items:
        if item["id"] == item_id:
            dish = item
            break
    
    if not dish:
        return {
            "status": "error",
            "message": "Блюдо не найдено"
        }
    
    user_allergens_list = [a.strip() for a in user_allergens.split(",")]
    
    found_allergens = []
    for allergen in user_allergens_list:
        if allergen in dish["allergens"]:
            found_allergens.append(allergen)
    
    if "орехи" in found_allergens or "морепродукты" in found_allergens:
        safety_level = "danger"
    elif found_allergens:
        safety_level = "warning"
    else:
        safety_level = "safe"
    
    return {
        "status": "success",
        "dish_name": dish["name"],
        "analysis": {
            "has_allergens": len(found_allergens) > 0,
            "allergens_found": found_allergens,
            "safety_level": safety_level,
            "message": get_safety_message(safety_level, found_allergens)
        }
    }

def get_safety_message(level: str, allergens: list):
    if level == "danger":
        return f"ОПАСНО! Блюдо содержит {', '.join(allergens)}. НЕ РЕКОМЕНДУЕТСЯ к употреблению!"
    elif level == "warning":
        return f"ВНИМАНИЕ! Блюдо содержит {', '.join(allergens)}. Будьте осторожны!"
    else:
        return "Безопасно! Аллергены не найдены."

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