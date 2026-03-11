"""Pydantic модели для системы заказов."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Статусы заказа."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderItemBase(BaseModel):
    """Базовая схема позиции заказа."""
    dish_id: int = Field(..., gt=0, description="ID блюда")
    quantity: int = Field(..., ge=1, le=20, description="Количество")
    special_requests: Optional[str] = Field(None, max_length=500, description="Особые пожелания")


class OrderItemCreate(OrderItemBase):
    """Схема для создания позиции заказа."""
    pass


class OrderItem(OrderItemBase):
    """Схема позиции заказа с дополнительными полями."""
    id: int
    order_id: int
    dish_name: str
    dish_price: int
    subtotal: int = Field(..., description="Стоимость позиции (цена * количество)")
    
    @field_validator('subtotal')
    @classmethod
    def validate_subtotal(cls, v, info):
        """Валидация подсчета стоимости."""
        values = info.data
        if 'dish_price' in values and 'quantity' in values:
            expected = values['dish_price'] * values['quantity']
            if v != expected:
                raise ValueError('Некорректная стоимость позиции')
        return v


class OrderBase(BaseModel):
    """Базовая схема заказа."""
    delivery_time: Optional[datetime] = Field(None, description="Желаемое время доставки")
    comments: Optional[str] = Field(None, max_length=1000, description="Комментарий к заказу")


class OrderCreate(OrderBase):
    """Схема для создания заказа."""
    items: List[OrderItemCreate] = Field(..., min_length=1, max_length=50, description="Позиции заказа")
    
    @field_validator('items')
    @classmethod
    def validate_unique_dishes(cls, v):
        """Проверка на уникальность блюд в заказе."""
        dish_ids = [item.dish_id for item in v]
        if len(dish_ids) != len(set(dish_ids)):
            raise ValueError('Блюда в заказе должны быть уникальными')
        return v


class Order(OrderBase):
    """Полная схема заказа."""
    id: int
    user_id: int
    user_email: str
    created_at: datetime
    status: OrderStatus = Field(..., description="Статус заказа")
    items: List[OrderItem]
    total_price: int = Field(..., ge=0, description="Общая стоимость заказа")
    estimated_ready_time: Optional[datetime] = Field(None, description="Ориентировочное время готовности")
    
    @field_validator('total_price')
    @classmethod
    def validate_total_price(cls, v, info):
        """Валидация общей стоимости."""
        values = info.data
        if 'items' in values:
            expected = sum(item.subtotal for item in values['items'])
            if v != expected:
                raise ValueError('Некорректная общая стоимость заказа')
        return v


class OrderStatusUpdate(BaseModel):
    """Схема для обновления статуса заказа."""
    status: OrderStatus = Field(..., description="Новый статус заказа")
    estimated_ready_time: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=500, description="Комментарий к изменению статуса")


class OrderListResponse(BaseModel):
    """Схема для списка заказов с пагинацией."""
    items: List[Order]
    total: int = Field(..., ge=0, description="Общее количество заказов")
    page: int = Field(..., ge=1, description="Номер страницы")
    size: int = Field(..., ge=1, le=100, description="Размер страницы")
    pages: int = Field(..., ge=0, description="Общее количество страниц")