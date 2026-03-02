"""Маршруты авторизации и работы с пользователем (ЛР по авторизации)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from app_config import ACCESS_TOKEN_EXPIRE_DELTA, ALGORITHM, SECRET_KEY
from core.db import create_user_record, get_user_by_email
from models.schemas import Token, TokenPayload, UserCreate, UserLogin, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


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
    )


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(user: UserCreate):
    """Регистрация пользователя (email + пароль + аллергены/диета)."""
    existing = get_user_by_email(user.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    password_hash = _hash_password(user.password)
    allergens_json = json.dumps(user.allergens or [], ensure_ascii=False)
    record = create_user_record(
        email=user.email,
        password_hash=password_hash,
        full_name=user.full_name,
        allergens_json=allergens_json,
        diet=user.diet,
    )

    return UserPublic(
        id=record["id"],
        email=record["email"],
        full_name=record["full_name"],
        allergens=user.allergens or [],
        diet=user.diet,
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Вход по email/паролю.

    Используется стандартный OAuth2PasswordRequestForm, поэтому ожидается:
    - username: email
    - password: пароль
    """
    record = get_user_by_email(form_data.username)
    if not record or not _verify_password(form_data.password, record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = _create_access_token(subject=record["email"])
    return Token(access_token=token)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)):
    """Профиль текущего авторизованного пользователя."""

    return current_user

