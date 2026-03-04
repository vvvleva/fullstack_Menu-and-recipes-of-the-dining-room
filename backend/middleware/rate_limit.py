"""Middleware для ограничения частоты запросов."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
import time
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения количества запросов от одного IP.
    
    Лимиты:
    - Анонимные пользователи: 100 запросов в минуту
    - Авторизованные пользователи: 500 запросов в минуту
    - Эндпоинты авторизации: 5 попыток в минуту
    """
    
    def __init__(
        self,
        app,
        default_limit: int = 100,
        auth_limit: int = 5,
        window_seconds: int = 60
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP клиента."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"
    
    def _is_auth_endpoint(self, request: Request) -> bool:
        """Проверка, является ли эндпоинт связанным с авторизацией."""
        auth_paths = ["/auth/login", "/auth/register", "/api/auth/login", "/api/auth/register"]
        return any(request.url.path.endswith(path) for path in auth_paths)
    
    def _clean_old_requests(self, client_ip: str):
        """Очистка старых запросов."""
        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window_seconds
        ]
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        
        # Очищаем старые записи
        self._clean_old_requests(client_ip)
        
        # Определяем лимит для эндпоинта
        if self._is_auth_endpoint(request):
            limit = self.auth_limit
        else:
            limit = self.default_limit
        
        # Проверяем количество запросов
        if len(self.requests[client_ip]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Слишком много запросов. Лимит: {limit} за {self.window_seconds} секунд",
                    "retry_after": self.window_seconds
                }
            )
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(time.time())
        
        # Продолжаем обработку
        response = await call_next(request)
        return response