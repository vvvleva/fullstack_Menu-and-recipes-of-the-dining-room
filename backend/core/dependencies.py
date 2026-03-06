"""Зависимости для проверки прав доступа и авторизации."""
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from jose import JWTError
import json

from routes.auth import get_current_user
from models.schemas import UserPublic


# OAuth2 схемы
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)

class OAuth2PasswordBearerOptional(OAuth2PasswordBearer):
    """Опциональная OAuth2 схема, не выбрасывающая ошибку при отсутствии токена."""
    async def __call__(self, request):
        try:
            return await super().__call__(request)
        except HTTPException:
            return None

oauth2_scheme_optional = OAuth2PasswordBearerOptional(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_admin(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    """
    Проверка, что текущий пользователь является администратором.
    
    Администраторы имеют поле role = "admin" в базе данных.
    """
    # Получаем полную запись пользователя из БД
    from core.db import get_user_by_email
    user_record = get_user_by_email(current_user.email)
    
    if not user_record or user_record.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Доступ запрещен. Требуются права администратора."
            }
        )
    
    return current_user


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional)) -> Optional[UserPublic]:
    """
    Опциональное получение текущего пользователя.
    Не вызывает ошибку, если пользователь не авторизован.
    """
    if not token:
        return None
    
    try:
        # Используем существующую функцию get_current_user, передавая ей токен
        from routes.auth import get_current_user as get_user
        return await get_user(token)
    except HTTPException:
        return None
    except JWTError:
        return None


async def check_dish_ownership(dish_id: int, current_user: UserPublic = Depends(get_current_user)) -> bool:
    """
    Проверка прав на редактирование блюда.
    Сейчас только админы могут редактировать.
    """
    from core.db import get_user_by_email
    user_record = get_user_by_email(current_user.email)
    return user_record and user_record.get("role") == "admin"


async def get_user_allergens(current_user: Optional[UserPublic] = Depends(get_current_user_optional)) -> list:
    """
    Получить список аллергенов текущего пользователя.
    Для неавторизованных возвращает пустой список.
    """
    if not current_user:
        return []
    return current_user.allergens


def require_allergens(allergens: list):
    """
    Декоратор для проверки наличия определенных аллергенов у пользователя.
    """
    async def dependency(current_user: UserPublic = Depends(get_current_user)):
        user_allergens = set(current_user.allergens)
        required_allergens = set(allergens)
        
        if not required_allergens.issubset(user_allergens):
            missing = required_allergens - user_allergens
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ALLERGENS_REQUIRED",
                    "message": f"У вас не указаны следующие аллергены: {', '.join(missing)}",
                    "missing_allergens": list(missing)
                }
            )
        return current_user
    return dependency