"""Сервис для работы с заказами."""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from core.db import get_connection, get_dish
from models.orders import OrderCreate, Order, OrderStatus, OrderItem
from core.logging import structured_logger


class OrderService:
    """Сервис для управления заказами."""
    
    PREPARATION_TIME = {
        "салаты": 10,
        "супы": 15,
        "горячее": 20,
        "гарниры": 10,
        "напитки": 5,
        "десерты": 10
    }
    
    def __init__(self):
        self.logger = structured_logger
    
    async def create_order(self, order_data: OrderCreate, user_id: int, user_email: str) -> Dict:
        """
        Создание нового заказа.
        
        Проверяет доступность блюд, рассчитывает стоимость и время приготовления.
        """
        items_with_details = []
        total_price = 0
        max_preparation_time = 0
        
        for item in order_data.items:
            dish = get_dish(item.dish_id)
            if not dish:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "DISH_NOT_FOUND",
                        "message": f"Блюдо с ID {item.dish_id} не найдено",
                        "dish_id": item.dish_id
                    }
                )
            
            if not dish["available"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "DISH_UNAVAILABLE",
                        "message": f"Блюдо '{dish['name']}' временно недоступно",
                        "dish_id": item.dish_id,
                        "dish_name": dish["name"]
                    }
                )
            
            subtotal = dish["price"] * item.quantity
            
            items_with_details.append({
                "dish_id": dish["id"],
                "dish_name": dish["name"],
                "dish_price": dish["price"],
                "quantity": item.quantity,
                "special_requests": item.special_requests,
                "subtotal": subtotal,
                "category": dish["category"]
            })
            
            total_price += subtotal
            
            prep_time = self.PREPARATION_TIME.get(dish["category"], 15)
            max_preparation_time = max(max_preparation_time, prep_time)
        
        estimated_ready_time = datetime.utcnow() + timedelta(minutes=max_preparation_time)
        
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (
                    user_id, user_email, total_price, delivery_time, 
                    comments, status, estimated_ready_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_email,
                    total_price,
                    order_data.delivery_time,
                    order_data.comments,
                    OrderStatus.PENDING,
                    estimated_ready_time
                )
            )
            order_id = cur.lastrowid
            
            for item in items_with_details:
                conn.execute(
                    """
                    INSERT INTO order_items (
                        order_id, dish_id, dish_name, dish_price, 
                        quantity, special_requests, subtotal
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        item["dish_id"],
                        item["dish_name"],
                        item["dish_price"],
                        item["quantity"],
                        item["special_requests"],
                        item["subtotal"]
                    )
                )
            
            order_row = conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()
            
            items_rows = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ?",
                (order_id,)
            ).fetchall()
        
        self.logger.log_order_event(
            order_id=order_id,
            user_id=user_id,
            event="order_created",
            details={
                "total_price": total_price,
                "items_count": len(items_with_details),
                "estimated_ready_time": estimated_ready_time.isoformat()
            }
        )
        
        return self._row_to_order(order_row, items_rows)
    
    async def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 20) -> List[Dict]:
        """Получить заказы пользователя с пагинацией."""
        with get_connection() as conn:
            orders_rows = conn.execute(
                """
                SELECT * FROM orders 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, skip)
            ).fetchall()
            
            orders = []
            for order_row in orders_rows:
                items_rows = conn.execute(
                    "SELECT * FROM order_items WHERE order_id = ?",
                    (order_row["id"],)
                ).fetchall()
                orders.append(self._row_to_order(order_row, items_rows))
            
            return orders
    
    async def get_order_by_id(self, order_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """Получить заказ по ID."""
        with get_connection() as conn:
            query = "SELECT * FROM orders WHERE id = ?"
            params = [order_id]
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            order_row = conn.execute(query, params).fetchone()
            
            if not order_row:
                return None
            
            items_rows = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ?",
                (order_id,)
            ).fetchall()
            
            return self._row_to_order(order_row, items_rows)
    
    async def update_order_status(
        self,
        order_id: int,
        status: str,
        user_id: int,
        is_admin: bool = False,
        estimated_ready_time: Optional[datetime] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Обновление статуса заказа.
        
        Обычные пользователи могут только отменять свои заказы.
        Администраторы могут менять любой статус.
        """
        with get_connection() as conn:
            order_row = conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()
            
            if not order_row:
                return None
            
            if not is_admin and order_row["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Нет прав на изменение этого заказа"
                    }
                )
            
            if not is_admin and status != OrderStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Вы можете только отменить свой заказ"
                    }
                )
            
            update_fields = ["status = ?"]
            params = [status]
            
            if estimated_ready_time:
                update_fields.append("estimated_ready_time = ?")
                params.append(estimated_ready_time)
            
            params.append(order_id)
            
            conn.execute(
                f"UPDATE orders SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
            
            items_rows = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ?",
                (order_id,)
            ).fetchall()
            
            updated_order = self._row_to_order(order_row, items_rows)
        
        self.logger.log_order_event(
            order_id=order_id,
            user_id=user_id,
            event=f"status_changed_to_{status}",
            details={
                "previous_status": order_row["status"],
                "comment": comment
            }
        )
        
        return updated_order
    
    def _row_to_order(self, order_row, items_rows) -> Dict:
        """Преобразование строки БД в словарь заказа."""
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
        
        return {
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
        }


order_service = OrderService()