"""Админские маршруты для управления системой."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timedelta

from core.db import get_connection, get_user_by_email, list_dishes
from models.schemas import UserPublic, MenuItemResponse
from routes.auth import get_current_user
from core.dependencies import get_current_admin
from services.order_service import order_service
from core.logging import structured_logger

router = APIRouter(prefix="/api/admin", tags=["Администрирование"])


@router.get("/stats", summary="Статистика системы")
async def get_system_stats(current_admin = Depends(get_current_admin)):
    """Получить статистику по системе (только для админов)."""
    with get_connection() as conn:
        users_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        
        dishes_count = conn.execute("SELECT COUNT(*) as count FROM dishes").fetchone()["count"]
        
        available_dishes = conn.execute(
            "SELECT COUNT(*) as count FROM dishes WHERE available = 1"
        ).fetchone()["count"]
        
        today = datetime.now().date()
        orders_today = conn.execute(
            """
            SELECT COUNT(*) as count, 
                   SUM(total_price) as revenue 
            FROM orders 
            WHERE date(created_at) = date(?)
            """,
            (today.isoformat(),)
        ).fetchone()
        
        orders_by_status = conn.execute(
            """
            SELECT status, COUNT(*) as count 
            FROM orders 
            GROUP BY status
            """
        ).fetchall()
        
        popular_dishes = conn.execute(
            """
            SELECT dish_name, SUM(quantity) as total_ordered
            FROM order_items
            GROUP BY dish_name
            ORDER BY total_ordered DESC
            LIMIT 5
            """
        ).fetchall()
    
    return {
        "status": "success",
        "data": {
            "users": {
                "total": users_count
            },
            "dishes": {
                "total": dishes_count,
                "available": available_dishes,
                "unavailable": dishes_count - available_dishes
            },
            "orders": {
                "today": {
                    "count": orders_today["count"] or 0,
                    "revenue": orders_today["revenue"] or 0
                },
                "by_status": [
                    {"status": row["status"], "count": row["count"]}
                    for row in orders_by_status
                ]
            },
            "popular_dishes": [
                {"name": row["dish_name"], "ordered": row["total_ordered"]}
                for row in popular_dishes
            ]
        }
    }


@router.get("/users", response_model=List[UserPublic])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_admin = Depends(get_current_admin)
):
    """Получить список всех пользователей."""
    with get_connection() as conn:
        users = conn.execute(
            "SELECT id, email, full_name, allergens_json, diet, role FROM users LIMIT ? OFFSET ?",
            (limit, skip)
        ).fetchall()
    
    result = []
    for user in users:
        import json
        result.append({
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "allergens": json.loads(user["allergens_json"] or "[]"),
            "diet": user["diet"]
        })
    
    return {
        "status": "success",
        "data": result
    }


@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: int,
    current_admin = Depends(get_current_admin)
):
    """Сделать пользователя администратором."""
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "Пользователь не найден"}
            )
        
        conn.execute(
            "UPDATE users SET role = 'admin' WHERE id = ?",
            (user_id,)
        )
        
        structured_logger.log_order_event(
            order_id=0,
            user_id=current_admin.id,
            event="user_promoted_to_admin",
            details={"target_user_id": user_id, "target_email": user["email"]}
        )
    
    return {
        "status": "success",
        "message": f"Пользователь {user['email']} теперь администратор"
    }


@router.get("/dishes/low-stock")
async def get_low_stock_dishes(
    threshold: int = 5,
    current_admin = Depends(get_current_admin)
):
    """Получить блюда с низким остатком."""
    return {
        "status": "success",
        "message": "Функциональность в разработке",
        "data": []
    }