"""Создание и настройка FastAPI-приложения."""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIR
from core.db import init_db
from core.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from routes.menu import router as menu_router
from routes.auth import router as auth_router
from routes.root import router as root_router
from routes.frontend import router as frontend_router


def create_app() -> FastAPI:
    """Фабрика приложения."""
    app = FastAPI(
        title="Столовая #2049 API",
        description="API для столовой с AI-анализом аллергенов",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    app.include_router(root_router)
    app.include_router(menu_router)
    app.include_router(auth_router)
    app.include_router(frontend_router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app


app = create_app()
