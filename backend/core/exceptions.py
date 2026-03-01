"""Обработчики исключений (ЛР №4)."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Единый формат ответа для HTTPException (404, 400 и т.д.)."""
    detail = exc.detail
    if isinstance(detail, dict):
        body = {"status": "error", **detail}
    else:
        body = {"status": "error", "code": "ERROR", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Единый формат ответа при ошибках валидации (422)."""
    errors = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"] if x != "body")
        errors.append({"field": loc, "message": err["msg"]})
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Ошибка валидации данных",
            "details": errors,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработка неожиданных ошибок (500)."""
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "Внутренняя ошибка сервера",
        },
    )
