"""Маршруты для отдачи фронтенда."""
from fastapi import APIRouter
from fastapi.responses import FileResponse

from config import FRONTEND_DIR

router = APIRouter(tags=["frontend"])


@router.get("/frontend")
@router.get("/frontend/{full_path:path}")
async def serve_frontend(full_path: str = ""):
    """Отдача фронтенда через FastAPI."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "Frontend files not found"}
