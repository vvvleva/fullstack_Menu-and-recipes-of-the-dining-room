"""Маршруты для работы с заказами."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status

from models.orders import OrderCreate, Order, OrderStatusUpdate, OrderListResponse
from services.order_service import order_service
from routes.auth import get_current_user
from core.dependencies import get_current_admin, get_current_user_optional
from models.schemas import UserPublic

router = APIRouter(prefix="/api/orders", tags=["Заказы"])


@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Создать новый заказ.
    
    Требуется авторизация. Проверяется доступность всех блюд.
    """
    order = await order_service.create_order(
        order_data=order_data,
        user_id=current_user.id,
        user_email=current_user.email
    )
    
    # Возвращаем только объект заказа, без обертки
    return order


@router.get("/", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Получить список своих заказов с пагинацией.
    """
    skip = (page - 1) * size
    orders = await order_service.get_user_orders(current_user.id, skip=skip, limit=size)
    
    from core.db import get_connection
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE user_id = ?",
            (current_user.id,)
        ).fetchone()["count"]
    
    return {
        "items": orders,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: int,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Получить детали конкретного заказа.
    """
    order = await order_service.get_order_by_id(order_id, user_id=current_user.id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": f"Заказ с ID {order_id} не найден"
            }
        )
    
    return order


@router.patch("/{order_id}/status", response_model=Order)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Обновить статус заказа.
    
    Пользователи могут только отменять свои заказы.
    Администраторы могут менять любой статус.
    """
    from core.db import get_user_by_email
    user_record = get_user_by_email(current_user.email)
    is_admin = user_record and user_record.get("role") == "admin"
    
    order = await order_service.update_order_status(
        order_id=order_id,
        status=status_update.status,
        user_id=current_user.id,
        is_admin=is_admin,
        estimated_ready_time=status_update.estimated_ready_time,
        comment=status_update.comment
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": f"Заказ с ID {order_id} не найден"
            }
        )
    
    return order


@router.delete("/{order_id}", response_model=Order)
async def cancel_order(
    order_id: int,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Отменить заказ (альтернативный способ через DELETE).
    """
    order = await order_service.update_order_status(
        order_id=order_id,
        status="cancelled",
        user_id=current_user.id,
        is_admin=False
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": f"Заказ с ID {order_id} не найден"
            }
        )
    
    return order


@router.get("/admin/all", response_model=OrderListResponse)
async def get_all_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
    current_admin: UserPublic = Depends(get_current_admin)
):
    """
    Получить все заказы (только для администраторов).
    """
    skip = (page - 1) * size
    
    from core.db import get_connection
    with get_connection() as conn:
        query = "SELECT * FROM orders WHERE 1=1"
        count_query = "SELECT COUNT(*) as count FROM orders WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(status)
        
        if user_id:
            query += " AND user_id = ?"
            count_query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        
        total = conn.execute(count_query, params).fetchone()["count"]
        
        orders_rows = conn.execute(query, params + [size, skip]).fetchall()
        
        orders = []
        for order_row in orders_rows:
            items_rows = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ?",
                (order_row["id"],)
            ).fetchall()
            
            items = []
            for item in items_rows:
                items.append({
                    "id": item["id"],
                    "order_id": item["order_id"],
                    "dish_id": item["dish_id"],
                    "dish_name": item["dish_name"],
                    "dish_price": item["dish_price"],
                    "quantity": item["quantity"],
                    "special_requests": item["special_requests"],
                    "subtotal": item["subtotal"]
                })
            
            orders.append({
                "id": order_row["id"],
                "user_id": order_row["user_id"],
                "user_email": order_row["user_email"],
                "created_at": order_row["created_at"],
                "status": order_row["status"],
                "items": items,
                "total_price": order_row["total_price"],
                "delivery_time": order_row["delivery_time"],
                "comments": order_row["comments"],
                "estimated_ready_time": order_row["estimated_ready_time"]
            })
    
    return {
        "items": orders,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }