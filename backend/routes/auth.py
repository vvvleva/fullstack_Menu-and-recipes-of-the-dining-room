"""Маршруты авторизации и работы с пользователем."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from config import ACCESS_TOKEN_EXPIRE_DELTA, ALGORITHM, SECRET_KEY
from core.db import create_user_record, get_user_by_email, update_user_profile
from core.security import hash_password, verify_password, validate_password_strength
from models.schemas import Token, TokenPayload, UserCreate, UserLogin, UserPublic, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _create_access_token(subject: str) -> str:
    now = datetime.now(tz=timezone.utc)
    expire = now + ACCESS_TOKEN_EXPIRE_DELTA
    to_encode = {"sub": subject, "exp": int(expire.timestamp())}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или просроченный токен",
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    payload = _decode_token(token)
    email = payload.sub
    record = get_user_by_email(email)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    allergens = []
    if record["allergens_json"]:
        try:
            allergens = json.loads(record["allergens_json"])
        except json.JSONDecodeError:
            allergens = []

    return UserPublic(
        id=record["id"],
        email=record["email"],
        full_name=record["full_name"],
        allergens=allergens,
        diet=record["diet"],
        role=record.get("role", "user"),
        is_active=record.get("is_active", True)
    )


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(user: UserCreate):
    """Регистрация пользователя (email + пароль + аллергены/диета)."""
    print(f"Попытка регистрации: {user.email}")
    
    # Проверяем сложность пароля
    is_valid, error_msg = validate_password_strength(user.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    existing = get_user_by_email(user.email)
    if existing:
        print(f"Пользователь уже существует: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    # Хешируем пароль
    password_hash = hash_password(user.password)
    print(f"Пароль захеширован")
    
    # Преобразуем список аллергенов в JSON строку
    allergens_json = json.dumps(user.allergens or [], ensure_ascii=False)
    print(f"Аллергены JSON: {allergens_json}")
    
    try:
        record = create_user_record(
            email=user.email,
            password_hash=password_hash,
            full_name=user.full_name,
            allergens_json=allergens_json,
            diet=user.diet,
        )
        print(f"Пользователь создан: {record}")
    except Exception as e:
        print(f"Ошибка при создании пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании пользователя",
        )

    return UserPublic(
        id=record["id"],
        email=record["email"],
        full_name=record["full_name"],
        allergens=user.allergens or [],
        diet=user.diet,
        role="user",
        is_active=True
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Вход по email/паролю.

    Используется стандартный OAuth2PasswordRequestForm, поэтому ожидается:
    - username: email
    - password: пароль
    """
    print(f"Попытка входа: {form_data.username}")
    
    record = get_user_by_email(form_data.username)
    if not record:
        print(f"Пользователь не найден: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    
    if not verify_password(form_data.password, record["password_hash"]):
        print(f"Неверный пароль для: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = _create_access_token(subject=record["email"])
    print(f"Успешный вход: {form_data.username}")
    return Token(access_token=token)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)):
    """Профиль текущего авторизованного пользователя."""
    return current_user


@router.put("/me", response_model=UserPublic)
async def update_me(
    user_update: UserUpdate,
    current_user: UserPublic = Depends(get_current_user)
):
    """Обновление профиля текущего пользователя."""
    print(f"Обновление профиля: {current_user.email}")
    print(f"Новые данные: {user_update}")
    
    try:
        # Преобразуем список аллергенов в JSON строку
        allergens_json = json.dumps(user_update.allergens or [], ensure_ascii=False)
        
        # Обновляем профиль в базе данных
        updated_record = update_user_profile(
            user_id=current_user.id,
            full_name=user_update.full_name,
            allergens_json=allergens_json,
            diet=user_update.diet
        )
        
        if not updated_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        print(f"Профиль обновлен: {updated_record}")
        
        return UserPublic(
            id=updated_record["id"],
            email=updated_record["email"],
            full_name=updated_record["full_name"],
            allergens=user_update.allergens or [],
            diet=updated_record["diet"],
            role=updated_record.get("role", "user"),
            is_active=updated_record.get("is_active", True)
        )
    except Exception as e:
        print(f"Ошибка при обновлении профиля: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении профиля"
        )