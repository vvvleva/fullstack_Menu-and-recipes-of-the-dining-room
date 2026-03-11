"""Корневые маршруты."""
from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["root"])


@router.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API Столовой #2049",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "menu": "/api/menu",
            "health": "/health",
            "frontend": "/frontend",
        },
    }


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "Столовая #2049 API",
    }