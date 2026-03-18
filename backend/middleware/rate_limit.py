"""Middleware для ограничения частоты запросов."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List
import time
from collections import defaultdict
import asyncio

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения количества запросов от одного IP.
    
    Лимиты:
    - По умолчанию: 100 запросов в минуту
    - Эндпоинты авторизации: 5 попыток в минуту
    - OPTIONS запросы (CORS preflight) не ограничиваются
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
        self.requests: Dict[str, List[float]] = defaultdict(list)
        # Блокировка для потокобезопасности
        self._lock = asyncio.Lock()
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP клиента."""
        # Пробуем получить IP из заголовков
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        forwarded_for = request.headers.get("X-Real-IP")
        if forwarded_for:
            return forwarded_for.strip()
        
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
        # Проверяем точное совпадение или окончание пути
        return any(path == p or path.endswith(p) for p in auth_paths)
    
    def _clean_old_requests(self, client_ip: str):
        """Очистка старых запросов."""
        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window_seconds
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Всегда пропускаем OPTIONS запросы (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Получаем IP клиента
        client_ip = self._get_client_ip(request)
        
        # Используем блокировку для безопасного доступа к self.requests
        async with self._lock:
            # Очищаем старые записи
            self._clean_old_requests(client_ip)
            
            # Определяем лимит в зависимости от эндпоинта
            limit = self.auth_limit if self._is_auth_endpoint(request) else self.default_limit
            
            # Проверяем превышение лимита
            if len(self.requests[client_ip]) >= limit:
                # Возвращаем ошибку 429
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
        
        try:
            # Продолжаем обработку запроса
            response = await call_next(request)
            return response
        except HTTPException:
            # Пробрасываем HTTP исключения дальше
            raise
        except Exception as e:
            # Логируем другие исключения и пробрасываем
            print(f"Ошибка в rate_limit middleware: {e}")
            raise