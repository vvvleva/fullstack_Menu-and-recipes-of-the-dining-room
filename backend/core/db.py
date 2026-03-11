"""
SQLite-хранилище для меню, состава блюд и пользователей.
Модуль предоставляет полный набор функций для работы с базой данных столовой.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Optional

from config import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    Создает и возвращает подключение к SQLite базе данных.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Инициализация базы данных при старте приложения.
    """
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS dishes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              price INTEGER NOT NULL,
              weight INTEGER NOT NULL,
              category TEXT NOT NULL,
              calories INTEGER NOT NULL,
              available INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS ingredients (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS allergens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS dish_ingredients (
              dish_id INTEGER NOT NULL,
              ingredient_id INTEGER NOT NULL,
              PRIMARY KEY (dish_id, ingredient_id),
              FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
              FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS dish_allergens (
              dish_id INTEGER NOT NULL,
              allergen_id INTEGER NOT NULL,
              PRIMARY KEY (dish_id, allergen_id),
              FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
              FOREIGN KEY (allergen_id) REFERENCES allergens(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              full_name TEXT,
              allergens_json TEXT DEFAULT '[]',
              diet TEXT
            );
            """
        )
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                total_price INTEGER NOT NULL,
                delivery_time TIMESTAMP,
                comments TEXT,
                estimated_ready_time TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                dish_id INTEGER NOT NULL,
                dish_name TEXT NOT NULL,
                dish_price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                special_requests TEXT,
                subtotal INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE RESTRICT
            );
            
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_dish_id ON order_items(dish_id);
            """
        )

        count = conn.execute("SELECT COUNT(*) AS c FROM dishes").fetchone()["c"]
        if count == 0:
            _seed(conn)


def _normalize_list(items: Iterable[str] | None) -> list[str]:
    """Нормализует список строк: приводит к нижнему регистру, удаляет пробелы, убирает дубликаты."""
    if not items:
        return []
    out: list[str] = []
    for x in items:
        s = (x or "").strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def _get_or_create_id(conn: sqlite3.Connection, table: str, name: str) -> int:
    """Получает ID записи по имени или создает новую, если не существует."""
    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(f"INSERT INTO {table}(name) VALUES (?)", (name,))
    return int(cur.lastrowid)


def _set_links(
    conn: sqlite3.Connection,
    *,
    dish_id: int,
    link_table: str,
    target_table: str,
    target_col: str,
    names: Iterable[str] | None,
) -> None:
    """Устанавливает связи между блюдом и ингредиентами/аллергенами."""
    normalized = _normalize_list(names)
    conn.execute(f"DELETE FROM {link_table} WHERE dish_id = ?", (dish_id,))
    for name in normalized:
        target_id = _get_or_create_id(conn, target_table, name)
        conn.execute(
            f"INSERT OR IGNORE INTO {link_table}(dish_id, {target_col}) VALUES (?, ?)",
            (dish_id, target_id),
        )


def _dish_row_to_dict(conn: sqlite3.Connection, dish_row: sqlite3.Row) -> dict[str, Any]:
    """Преобразует строку из таблицы dishes в словарь с полной информацией о блюде."""
    dish_id = int(dish_row["id"])

    ingredients = [
        r["name"]
        for r in conn.execute(
            """
            SELECT i.name
            FROM dish_ingredients di
            JOIN ingredients i ON i.id = di.ingredient_id
            WHERE di.dish_id = ?
            ORDER BY i.name
            """,
            (dish_id,),
        ).fetchall()
    ]

    allergens = [
        r["name"]
        for r in conn.execute(
            """
            SELECT a.name
            FROM dish_allergens da
            JOIN allergens a ON a.id = da.allergen_id
            WHERE da.dish_id = ?
            ORDER BY a.name
            """,
            (dish_id,),
        ).fetchall()
    ]

    return {
        "id": dish_id,
        "name": dish_row["name"],
        "price": int(dish_row["price"]),
        "weight": int(dish_row["weight"]),
        "category": dish_row["category"],
        "ingredients": ingredients,
        "allergens": allergens,
        "calories": int(dish_row["calories"]),
        "available": bool(dish_row["available"]),
    }


def list_dishes(*, category: str | None = None, only_available: bool = False) -> list[dict[str, Any]]:
    """Возвращает список блюд с возможностью фильтрации."""
    with get_connection() as conn:
        where: list[str] = []
        params: list[Any] = []
        
        if category is not None:
            where.append("category = ?")
            params.append(category.strip().lower())
        if only_available:
            where.append("available = 1")
            
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        rows = conn.execute(
            f"SELECT id, name, price, weight, category, calories, available FROM dishes{where_sql} ORDER BY id",
            tuple(params),
        ).fetchall()
        
        return [_dish_row_to_dict(conn, r) for r in rows]


def get_dish(dish_id: int) -> dict[str, Any] | None:
    """Возвращает информацию о конкретном блюде по ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        if not row:
            return None
        return _dish_row_to_dict(conn, row)


def create_dish(payload: dict[str, Any]) -> dict[str, Any]:
    """Создает новое блюдо в базе данных."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO dishes(name, price, weight, category, calories, available)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"].strip(),
                int(payload["price"]),
                int(payload["weight"]),
                payload["category"].strip().lower(),
                int(payload["calories"]),
                1 if payload.get("available", True) else 0,
            ),
        )
        dish_id = int(cur.lastrowid)
        
        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_ingredients",
            target_table="ingredients",
            target_col="ingredient_id",
            names=payload.get("ingredients"),
        )
        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_allergens",
            target_table="allergens",
            target_col="allergen_id",
            names=payload.get("allergens"),
        )
        
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        return _dish_row_to_dict(conn, row)


def update_dish(dish_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Обновляет информацию о блюде."""
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM dishes WHERE id = ?", (dish_id,)).fetchone()
        if not existing:
            return None

        conn.execute(
            """
            UPDATE dishes
            SET name = ?, price = ?, weight = ?, category = ?, calories = ?, available = ?
            WHERE id = ?
            """,
            (
                payload["name"].strip(),
                int(payload["price"]),
                int(payload["weight"]),
                payload["category"].strip().lower(),
                int(payload["calories"]),
                1 if payload.get("available", True) else 0,
                dish_id,
            ),
        )

        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_ingredients",
            target_table="ingredients",
            target_col="ingredient_id",
            names=payload.get("ingredients"),
        )
        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_allergens",
            target_table="allergens",
            target_col="allergen_id",
            names=payload.get("allergens"),
        )

        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        return _dish_row_to_dict(conn, row)


def delete_dish(dish_id: int) -> dict[str, Any] | None:
    """Удаляет блюдо из базы данных."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        if not row:
            return None
            
        data = _dish_row_to_dict(conn, row)
        conn.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        return data


def _seed(conn: sqlite3.Connection) -> None:
    """Заполнение базы тестовыми данными."""
    seed_items: list[dict[str, Any]] = [
        {
            "name": "Цезарь с курицей",
            "price": 350,
            "weight": 250,
            "category": "салаты",
            "ingredients": ["курица", "салат айсберг", "соус", "пармезан", "грецкий орех", "гренки"],
            "allergens": ["орехи", "глютен", "лактоза"],
            "calories": 420,
            "available": True,
        },
        {
            "name": "Греческий салат",
            "price": 300,
            "weight": 200,
            "category": "салаты",
            "ingredients": ["помидоры", "огурцы", "фета", "оливки", "оливковое масло"],
            "allergens": ["лактоза"],
            "calories": 250,
            "available": True,
        },
        {
            "name": "Борщ",
            "price": 280,
            "weight": 300,
            "category": "супы",
            "ingredients": ["свекла", "капуста", "картофель", "говядина", "сметана"],
            "allergens": ["лактоза"],
            "calories": 180,
            "available": True,
        },
        {
            "name": "Котлеты с пюре",
            "price": 380,
            "weight": 350,
            "category": "горячее",
            "ingredients": ["котлеты", "картофельное пюре", "соус"],
            "allergens": ["глютен", "лактоза"],
            "calories": 550,
            "available": True,
        },
    ]

    for item in seed_items:
        cur = conn.execute(
            """
            INSERT INTO dishes(name, price, weight, category, calories, available)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item["name"],
                int(item["price"]),
                int(item["weight"]),
                item["category"],
                int(item["calories"]),
                1 if item.get("available", True) else 0,
            ),
        )
        dish_id = int(cur.lastrowid)
        
        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_ingredients",
            target_table="ingredients",
            target_col="ingredient_id",
            names=item.get("ingredients"),
        )
        _set_links(
            conn,
            dish_id=dish_id,
            link_table="dish_allergens",
            target_table="allergens",
            target_col="allergen_id",
            names=item.get("allergens"),
        )


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    """Получает информацию о пользователе по email."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, full_name, allergens_json, diet, role, is_active FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "email": row["email"],
            "password_hash": row["password_hash"],
            "full_name": row["full_name"],
            "allergens_json": row["allergens_json"],
            "diet": row["diet"],
            "role": row["role"] if "role" in row.keys() else "user",
            "is_active": bool(row["is_active"]) if "is_active" in row.keys() else True,
        }


def create_user_record(
    *,
    email: str,
    password_hash: str,
    full_name: Optional[str],
    allergens_json: str,
    diet: Optional[str],
) -> dict[str, Any]:
    """Создает новую запись пользователя в базе данных."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO users(email, password_hash, full_name, allergens_json, diet)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.lower(), password_hash, full_name, allergens_json, diet),
        )
        user_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT id, email, password_hash, full_name, allergens_json, diet FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return {
            "id": int(row["id"]),
            "email": row["email"],
            "password_hash": row["password_hash"],
            "full_name": row["full_name"],
            "allergens_json": row["allergens_json"],
            "diet": row["diet"],
        }


def get_user_orders_count(user_id: int) -> int:
    """Получить количество заказов пользователя."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return result["count"] if result else 0


def get_order_stats() -> dict:
    """Получить статистику по заказам."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as count FROM orders").fetchone()["count"]
        
        by_status = conn.execute(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        ).fetchall()
        
        revenue = conn.execute(
            "SELECT SUM(total_price) as total FROM orders WHERE status != 'cancelled'"
        ).fetchone()["total"] or 0
        
        return {
            "total_orders": total,
            "by_status": {row["status"]: row["count"] for row in by_status},
            "total_revenue": revenue
        }