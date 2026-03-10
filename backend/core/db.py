"""
SQLite-хранилище для меню, состава блюд и пользователей.
Модуль предоставляет полный набор функций для работы с базой данных столовой.
"""

from __future__ import annotations  # Для использования аннотаций типов в более старых версиях Python

import sqlite3
from typing import Any, Iterable, Optional

from config import DATA_DIR, DB_PATH  # Импорт конфигурации с путями к файлам БД


def get_connection() -> sqlite3.Connection:
    """
    Создает и возвращает подключение к SQLite базе данных.
    
    Returns:
        sqlite3.Connection: Объект подключения с настроенной row_factory
        
    Особенности:
        - Автоматически создает директорию для БД если её нет
        - Устанавливает row_factory = sqlite3.Row для доступа по именам колонок
        - Включает поддержку внешних ключей (foreign keys)
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # Создаем папку для БД
    conn = sqlite3.connect(DB_PATH)  # Подключаемся к БД
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по именам
    conn.execute("PRAGMA foreign_keys = ON;")  # Включаем поддержку внешних ключей
    return conn


def init_db() -> None:
    """
    Инициализация базы данных при старте приложения.
    Создает все необходимые таблицы и заполняет тестовыми данными.
    """
    with get_connection() as conn:  # Используем контекстный менеджер для автоматического закрытия
        # Создаем основные таблицы
        conn.executescript(
            """
            -- Таблица блюд
            CREATE TABLE IF NOT EXISTS dishes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Автоинкрементный ID
              name TEXT NOT NULL,                     -- Название блюда
              price INTEGER NOT NULL,                  -- Цена в рублях
              weight INTEGER NOT NULL,                 -- Вес в граммах
              category TEXT NOT NULL,                   -- Категория (салаты, супы и т.д.)
              calories INTEGER NOT NULL,                -- Калорийность
              available INTEGER NOT NULL DEFAULT 1      -- Доступность (0/1)
            );

            -- Таблица ингредиентов (справочник)
            CREATE TABLE IF NOT EXISTS ingredients (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE                 -- Уникальное название ингредиента
            );

            -- Таблица аллергенов (справочник)
            CREATE TABLE IF NOT EXISTS allergens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE                 -- Уникальное название аллергена
            );

            -- Связь блюд с ингредиентами (многие ко многим)
            CREATE TABLE IF NOT EXISTS dish_ingredients (
              dish_id INTEGER NOT NULL,
              ingredient_id INTEGER NOT NULL,
              PRIMARY KEY (dish_id, ingredient_id),     -- Составной первичный ключ
              FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,        -- При удалении блюда удаляются связи
              FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT  -- Нельзя удалить используемый ингредиент
            );

            -- Связь блюд с аллергенами (многие ко многим)
            CREATE TABLE IF NOT EXISTS dish_allergens (
              dish_id INTEGER NOT NULL,
              allergen_id INTEGER NOT NULL,
              PRIMARY KEY (dish_id, allergen_id),
              FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
              FOREIGN KEY (allergen_id) REFERENCES allergens(id) ON DELETE RESTRICT
            );

            -- Таблица пользователей
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL UNIQUE,                -- Email как уникальный идентификатор
              password_hash TEXT NOT NULL,               -- Хеш пароля (не сам пароль!)
              full_name TEXT,                              -- Полное имя
              allergens_json TEXT DEFAULT '[]',           -- Аллергены в JSON формате
              diet TEXT                                    -- Диетические предпочтения
            );
            """
        )
        
        # Добавляем новые поля в users (с проверкой существования)
        # Используем try-except, так как SQLite не поддерживает IF NOT EXISTS для колонок
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")  # Роль (user/admin)
        except sqlite3.OperationalError:
            pass  # Поле уже существует - игнорируем ошибку
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")  # Активен ли пользователь
        except sqlite3.OperationalError:
            pass
        
        # Создаем таблицы заказов
        conn.executescript(
            """
            -- Таблица заказов
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,                    -- ID пользователя
                user_email TEXT NOT NULL,                      -- Email на момент заказа
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Время создания
                status TEXT NOT NULL DEFAULT 'pending',        -- Статус (pending, confirmed, preparing, ready, delivered, cancelled)
                total_price INTEGER NOT NULL,                  -- Общая стоимость
                delivery_time TIMESTAMP,                        -- Время доставки
                comments TEXT,                                  -- Комментарии к заказу
                estimated_ready_time TIMESTAMP,                 -- Ориентировочное время готовности
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            -- Таблица позиций в заказе
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,                      -- ID заказа
                dish_id INTEGER NOT NULL,                        -- ID блюда
                dish_name TEXT NOT NULL,                         -- Название блюда на момент заказа
                dish_price INTEGER NOT NULL,                     -- Цена на момент заказа
                quantity INTEGER NOT NULL,                       -- Количество
                special_requests TEXT,                           -- Особые пожелания
                subtotal INTEGER NOT NULL,                       -- Сумма по позиции (price * quantity)
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE RESTRICT
            );
            
            -- Индексы для ускорения поиска
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_dish_id ON order_items(dish_id);
            """
        )

        # Заполняем тестовыми данными если таблица пуста
        count = conn.execute("SELECT COUNT(*) AS c FROM dishes").fetchone()["c"]
        if count == 0:
            _seed(conn)  # Вызываем внутреннюю функцию заполнения


def _normalize_list(items: Iterable[str] | None) -> list[str]:
    """
    Нормализует список строк: приводит к нижнему регистру, удаляет пробелы, убирает дубликаты.
    
    Args:
        items: Итерируемый объект со строками или None
        
    Returns:
        list[str]: Нормализованный список уникальных строк
    """
    if not items:
        return []
    out: list[str] = []
    for x in items:
        s = (x or "").strip().lower()  # Убираем пробелы и приводим к нижнему регистру
        if s and s not in out:          # Проверяем на пустоту и уникальность
            out.append(s)
    return out


def _get_or_create_id(conn: sqlite3.Connection, table: str, name: str) -> int:
    """
    Получает ID записи по имени или создает новую, если не существует.
    
    Args:
        conn: Подключение к БД
        table: Имя таблицы (ingredients или allergens)
        name: Название элемента
        
    Returns:
        int: ID существующей или новой записи
    """
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
    """
    Устанавливает связи между блюдом и ингредиентами/аллергенами.
    
    Args:
        conn: Подключение к БД
        dish_id: ID блюда
        link_table: Таблица связей (dish_ingredients или dish_allergens)
        target_table: Целевая таблица (ingredients или allergens)
        target_col: Название колонки с ID в таблице связей
        names: Список названий для связывания
    """
    normalized = _normalize_list(names)
    # Удаляем старые связи
    conn.execute(f"DELETE FROM {link_table} WHERE dish_id = ?", (dish_id,))
    # Создаем новые связи
    for name in normalized:
        target_id = _get_or_create_id(conn, target_table, name)
        conn.execute(
            f"INSERT OR IGNORE INTO {link_table}(dish_id, {target_col}) VALUES (?, ?)",
            (dish_id, target_id),
        )


def _dish_row_to_dict(conn: sqlite3.Connection, dish_row: sqlite3.Row) -> dict[str, Any]:
    """
    Преобразует строку из таблицы dishes в словарь с полной информацией о блюде.
    Добавляет списки ингредиентов и аллергенов из связанных таблиц.
    
    Args:
        conn: Подключение к БД
        dish_row: Строка из таблицы dishes
        
    Returns:
        dict: Полное представление блюда
    """
    dish_id = int(dish_row["id"])

    # Получаем список ингредиентов для блюда
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

    # Получаем список аллергенов для блюда
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


# ==================== ОСНОВНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БЛЮДАМИ ====================

def list_dishes(*, category: str | None = None, only_available: bool = False) -> list[dict[str, Any]]:
    """
    Возвращает список блюд с возможностью фильтрации.
    
    Args:
        category: Фильтр по категории (опционально)
        only_available: Только доступные блюда
        
    Returns:
        list[dict]: Список блюд
    """
    with get_connection() as conn:
        where: list[str] = []
        params: list[Any] = []
        
        # Формируем условия WHERE динамически
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
    """
    Возвращает информацию о конкретном блюде по ID.
    
    Args:
        dish_id: ID блюда
        
    Returns:
        dict | None: Информация о блюде или None если не найдено
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        if not row:
            return None
        return _dish_row_to_dict(conn, row)


def create_dish(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Создает новое блюдо в базе данных.
    
    Args:
        payload: Словарь с данными блюда
        
    Returns:
        dict: Созданное блюдо с полной информацией
    """
    with get_connection() as conn:
        # Вставляем основную информацию о блюде
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
        
        # Создаем связи с ингредиентами и аллергенами
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
        
        # Возвращаем полную информацию о созданном блюде
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        return _dish_row_to_dict(conn, row)


def update_dish(dish_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Обновляет информацию о блюде.
    
    Args:
        dish_id: ID блюда для обновления
        payload: Новые данные
        
    Returns:
        dict | None: Обновленное блюдо или None если не найдено
    """
    with get_connection() as conn:
        # Проверяем существование блюда
        existing = conn.execute("SELECT id FROM dishes WHERE id = ?", (dish_id,)).fetchone()
        if not existing:
            return None

        # Обновляем основную информацию
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

        # Обновляем связи
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

        # Возвращаем обновленное блюдо
        row = conn.execute(
            "SELECT id, name, price, weight, category, calories, available FROM dishes WHERE id = ?",
            (dish_id,),
        ).fetchone()
        return _dish_row_to_dict(conn, row)


def delete_dish(dish_id: int) -> dict[str, Any] | None:
    """
    Удаляет блюдо из базы данных.
    
    Args:
        dish_id: ID блюда для удаления
        
    Returns:
        dict | None: Информация об удаленном блюде или None если не найдено
    """
    with get_connection() as conn:
        # Получаем информацию о блюде до удаления
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
    """
    Заполнение базы тестовыми данными.
    Внутренняя функция, вызывается при инициализации пустой БД.
    
    Args:
        conn: Подключение к БД
    """
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
        # Вставляем блюдо
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
        
        # Создаем связи с ингредиентами и аллергенами
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


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ====================

def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    """
    Получает информацию о пользователе по email.
    
    Args:
        email: Email пользователя
        
    Returns:
        Optional[dict]: Информация о пользователе или None
    """
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
    """
    Создает новую запись пользователя в базе данных.
    
    Args:
        email: Email пользователя
        password_hash: Хеш пароля
        full_name: Полное имя
        allergens_json: Аллергены в JSON формате
        diet: Диетические предпочтения
        
    Returns:
        dict: Созданная запись пользователя
    """
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


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАКАЗАМИ ====================

def get_user_orders_count(user_id: int) -> int:
    """
    Получить количество заказов пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        int: Количество заказов
    """
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return result["count"] if result else 0


def get_order_stats() -> dict:
    """
    Получить статистику по заказам.
    
    Returns:
        dict: Статистика с общим количеством, распределением по статусам и выручкой
    """
    with get_connection() as conn:
        # Общее количество заказов
        total = conn.execute("SELECT COUNT(*) as count FROM orders").fetchone()["count"]
        
        # Количество по статусам
        by_status = conn.execute(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        ).fetchall()
        
        # Общая выручка (исключая отмененные заказы)
        revenue = conn.execute(
            "SELECT SUM(total_price) as total FROM orders WHERE status != 'cancelled'"
        ).fetchone()["total"] or 0
        
        return {
            "total_orders": total,
            "by_status": {row["status"]: row["count"] for row in by_status},
            "total_revenue": revenue
        }