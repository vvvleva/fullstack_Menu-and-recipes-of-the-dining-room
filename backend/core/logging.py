"""Структурированное логирование для мониторинга."""
import logging
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("dining_room")


class StructuredLogger:
    """Структурированный логгер с JSON форматом."""
    
    @staticmethod
    def _get_client_info(request: Request) -> Dict[str, Any]:
        """Получить информацию о клиенте."""
        return {
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "referer": request.headers.get("referer", "unknown")
        }
    
    def log_request(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        user_id: Optional[int] = None
    ) -> None:
        """Логирование HTTP запроса."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "request",
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client": self._get_client_info(request),
            "user_id": user_id
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        user_id: Optional[int] = None
    ) -> None:
        """Логирование ошибок."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "error",
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "user_id": user_id
        }
        if request:
            log_entry["path"] = request.url.path
            log_entry["method"] = request.method
        
        logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_order_event(
        self,
        order_id: int,
        user_id: int,
        event: str,
        details: Optional[Dict] = None
    ) -> None:
        """Логирование событий заказа."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "order_event",
            "order_id": order_id,
            "user_id": user_id,
            "event": event,
            "details": details or {}
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_allergen_alert(
        self,
        user_id: int,
        dish_id: int,
        allergens_found: list,
        risk_level: str
    ) -> None:
        """Логирование срабатываний аллергенов."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "allergen_alert",
            "user_id": user_id,
            "dish_id": dish_id,
            "allergens_found": allergens_found,
            "risk_level": risk_level
        }
        logger.warning(json.dumps(log_entry, ensure_ascii=False))


structured_logger = StructuredLogger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        user_id = getattr(request.state, "user_id", None)
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            structured_logger.log_request(request, response, duration_ms, user_id)
            
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            structured_logger.log_error(e, request, user_id)
            raise