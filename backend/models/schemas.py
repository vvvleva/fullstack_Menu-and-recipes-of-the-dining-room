"""Pydantic-схемы: блюда и пользователи (авторизация)."""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# --- Блюда ---

# Допустимые категории блюд
ALLOWED_CATEGORIES = {"салаты", "супы", "горячее", "гарниры", "напитки", "десерты"}


class MenuItemBase(BaseModel):
    """Базовая схема блюда."""

    name: str = Field(..., min_length=1, max_length=200, description="Название блюда")
    price: int = Field(..., ge=1, le=100_000, description="Цена в рублях")
    weight: int = Field(..., ge=1, le=5000, description="Вес в граммах")
    category: str = Field(..., min_length=1, max_length=50, description="Категория")
    ingredients: list[str] = Field(default_factory=list, description="Список ингредиентов")
    allergens: list[str] = Field(default_factory=list, description="Список аллергенов")
    calories: int = Field(..., ge=0, le=5000, description="Калорийность")
    available: bool = Field(default=True, description="Доступно для заказа")

    @field_validator("category")
    @classmethod
    def category_must_be_allowed(cls, v: str) -> str:
        v_lower = v.strip().lower()
        if v_lower not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Категория должна быть одной из: {', '.join(sorted(ALLOWED_CATEGORIES))}"
            )
        return v_lower

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Название не может быть пустым")
        return stripped


class MenuItemCreate(MenuItemBase):
    """Схема для создания блюда (POST)."""

    pass


class MenuItemUpdate(BaseModel):
    """Схема для обновления блюда (PUT) — все поля опциональны для частичного обновления."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[int] = Field(None, ge=1, le=100_000)
    weight: Optional[int] = Field(None, ge=1, le=5000)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    ingredients: Optional[list[str]] = None
    allergens: Optional[list[str]] = None
    calories: Optional[int] = Field(None, ge=0, le=5000)
    available: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def category_must_be_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_lower = v.strip().lower()
        if v_lower not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Категория должна быть одной из: {', '.join(sorted(ALLOWED_CATEGORIES))}"
            )
        return v_lower

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Название не может быть пустым")
        return stripped


class MenuItemResponse(BaseModel):
    """Схема ответа с блюдом."""

    id: int
    name: str
    price: int
    weight: int
    category: str
    ingredients: list[str]
    allergens: list[str]
    calories: int
    available: bool


# --- Пользователи и авторизация ---


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя (логин)")
    full_name: Optional[str] = Field(None, max_length=200, description="Полное имя")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Пароль")
    allergens: list[str] = Field(default_factory=list, description="Аллергены пользователя")
    diet: Optional[str] = Field(None, max_length=100, description="Тип диеты")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(UserBase):
    id: int
    allergens: list[str] = Field(default_factory=list)
    diet: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
