"""Упрощенный middleware для ограничения частоты запросов."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List
import time
from collections import defaultdict

class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Упрощенный middleware для ограничения количества запросов.
    Без сложных зависимостей и с правильной обработкой ошибок.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        auth_requests_per_minute: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP клиента."""
        # Пробуем получить IP из заголовков
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Если нет заголовков, берем из client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_auth_endpoint(self, request: Request) -> bool:
        """Проверка, является ли эндпоинт связанным с авторизацией."""
        auth_paths = [
            "/auth/login", 
            "/auth/register", 
            "/api/auth/login", 
            "/api/auth/register"
        ]
        path = request.url.path
        return any(path == p or path.endswith(p) for p in auth_paths)
    
    async def dispatch(self, request: Request, call_next):
        # Всегда пропускаем OPTIONS запросы (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Получаем IP клиента
        client_ip = self._get_client_ip(request)
        
        # Очищаем старые записи (старше 60 секунд)
        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < 60
        ]
        
        # Определяем лимит в зависимости от эндпоинта
        if self._is_auth_endpoint(request):
            limit = self.auth_requests_per_minute
        else:
            limit = self.requests_per_minute
        
        # Проверяем превышение лимита
        if len(self.requests[client_ip]) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Слишком много запросов. Лимит: {limit} запросов в минуту",
                    "retry_after": 60
                }
            )
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(now)
        
        try:
            # Продолжаем обработку запроса
            response = await call_next(request)
            return response
        except Exception as e:
            # Логируем ошибку, но не перехватываем её
            print(f"Ошибка при обработке запроса: {e}")
            raise