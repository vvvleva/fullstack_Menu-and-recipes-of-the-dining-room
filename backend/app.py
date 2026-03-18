"""Создание и настройка FastAPI-приложения."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import AsyncGenerator
import asyncio

from config import FRONTEND_DIR
from core.db import init_db
from core.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from core.logging import LoggingMiddleware
from middleware.simple_rate_limit import SimpleRateLimitMiddleware

from routes.menu import router as menu_router
from routes.auth import router as auth_router
from routes.orders import router as orders_router
from routes.admin import router as admin_router
from routes.root import router as root_router
from routes.frontend import router as frontend_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Управление жизненным циклом приложения.
    Выполняется при старте и завершении работы приложения.
    """
    print("Запуск приложения...")
    try:
        await asyncio.to_thread(init_db)
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        raise
    
    yield
    
    print("Остановка приложения...")


def create_app() -> FastAPI:
    """Фабрика приложения."""
    app = FastAPI(
        title="Столовая #2049 API",
        description="API для столовой с AI-анализом аллергенов",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS должен быть ПЕРВЫМ middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Затем добавляем остальные middleware
    app.add_middleware(LoggingMiddleware)
    
    # Раскомментируйте для включения rate limit с увеличенными лимитами
    app.add_middleware(
        SimpleRateLimitMiddleware,
        requests_per_minute=200,      # Увеличено до 200
        auth_requests_per_minute=50    # Увеличено до 50
    )

    # Монтируем статические файлы, если папка существует
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    # Подключаем роутеры
    app.include_router(root_router)
    app.include_router(auth_router)
    app.include_router(menu_router)
    app.include_router(orders_router)
    app.include_router(admin_router)
    app.include_router(frontend_router)

    # Обработчики исключений
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app


app = create_app()