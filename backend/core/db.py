"""SQLite-хранилище для меню и состава блюд."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from config import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
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
            """
        )

        count = conn.execute("SELECT COUNT(*) AS c FROM dishes").fetchone()["c"]
        if count == 0:
            _seed(conn)


def _normalize_list(items: Iterable[str] | None) -> list[str]:
    if not items:
        return []
    out: list[str] = []
    for x in items:
        s = (x or "").strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def _get_or_create_id(conn: sqlite3.Connection, table: str, name: str) -> int:
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
    normalized = _normalize_list(names)
    conn.execute(f"DELETE FROM {link_table} WHERE dish_id = ?", (dish_id,))
    for name in normalized:
        target_id = _get_or_create_id(conn, target_table, name)
        conn.execute(
            f"INSERT OR IGNORE INTO {link_table}(dish_id, {target_col}) VALUES (?, ?)",
            (dish_id, target_id),
        )


def _dish_row_to_dict(conn: sqlite3.Connection, dish_row: sqlite3.Row) -> dict[str, Any]:
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
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        if not row:
            return None
        return _dish_row_to_dict(conn, row)


def create_dish(payload: dict[str, Any]) -> dict[str, Any]:
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

