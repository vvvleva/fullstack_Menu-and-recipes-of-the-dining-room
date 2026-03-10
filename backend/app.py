"""Создание и настройка FastAPI-приложения."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import AsyncGenerator
import asyncio

from config import FRONTEND_DIR
from core.db import init_db  # Это синхронная функция
from core.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from core.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware

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
    # Startup
    print("Starting up...")
    try:
        # Запускаем синхронную функцию в отдельном потоке
        await asyncio.to_thread(init_db)
        print("Database initialized")
    except Exception as e:
        print(f"Error during startup: {e}")
        raise  # Пробрасываем ошибку дальше
    
    yield  # Приложение работает здесь
    
    # Shutdown
    print("Shutting down...")
    # Здесь можно добавить cleanup, закрытие соединений и т.д.
    print("Cleanup completed")


def create_app() -> FastAPI:
    """Фабрика приложения."""
    app = FastAPI(
        title="Столовая #2049 API",
        description="API для столовой с AI-анализом аллергенов",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Логирование
    app.add_middleware(LoggingMiddleware)
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Статика
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    # Роуты
    app.include_router(root_router)
    app.include_router(auth_router)
    app.include_router(menu_router)
    app.include_router(orders_router)
    app.include_router(admin_router)
    app.include_router(frontend_router)

    # Обработчики ошибок
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app


app = create_app()