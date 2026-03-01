"""Маршруты меню и AI-анализа. CRUD для блюд (ЛР №4)."""
from fastapi import APIRouter, HTTPException

from models.schemas import MenuItemBase, MenuItemUpdate

router = APIRouter(prefix="/api", tags=["menu"])


# База данных в памяти (будет заменена на БД в следующих ЛР)
menu_items: list[dict] = [
    {
        "id": 1,
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
        "id": 2,
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
        "id": 3,
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
        "id": 4,
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


def _next_id() -> int:
    """Генерация следующего ID."""
    if not menu_items:
        return 1
    return max(item["id"] for item in menu_items) + 1


def _find_index(item_id: int) -> int:
    """Индекс блюда по ID. Вызывает HTTPException 404, если не найдено."""
    for i, item in enumerate(menu_items):
        if item["id"] == item_id:
            return i
    raise HTTPException(
        status_code=404,
        detail={
            "code": "NOT_FOUND",
            "message": "Блюдо не найдено",
            "item_id": item_id,
        },
    )


# ——— READ ———

@router.get("/menu")
async def get_menu():
    """Получить всё меню."""
    return {
        "status": "success",
        "data": menu_items,
        "count": len(menu_items),
    }


@router.get("/menu/category/{category}")
async def get_menu_by_category(category: str):
    """Получить блюда по категории. Маршрут должен быть выше /menu/{item_id}."""
    filtered = [item for item in menu_items if item["category"] == category and item["available"]]
    return {
        "status": "success",
        "category": category,
        "data": filtered,
        "count": len(filtered),
    }


@router.get("/menu/{item_id}")
async def get_menu_item(item_id: int):
    """Получить блюдо по ID."""
    idx = _find_index(item_id)
    return {
        "status": "success",
        "data": menu_items[idx],
    }


# ——— CREATE ———

@router.post("/menu", status_code=201)
async def create_menu_item(payload: MenuItemBase):
    """Создать новое блюдо. Валидация через Pydantic."""
    new_id = _next_id()
    new_item = {
        "id": new_id,
        "name": payload.name,
        "price": payload.price,
        "weight": payload.weight,
        "category": payload.category,
        "ingredients": payload.ingredients,
        "allergens": payload.allergens,
        "calories": payload.calories,
        "available": payload.available,
    }
    menu_items.append(new_item)
    return {
        "status": "success",
        "message": "Блюдо создано",
        "data": new_item,
    }


# ——— UPDATE ———

@router.put("/menu/{item_id}")
async def update_menu_item(item_id: int, payload: MenuItemBase):
    """Полное обновление блюда (PUT)."""
    idx = _find_index(item_id)
    updated = {
        "id": item_id,
        "name": payload.name,
        "price": payload.price,
        "weight": payload.weight,
        "category": payload.category,
        "ingredients": payload.ingredients,
        "allergens": payload.allergens,
        "calories": payload.calories,
        "available": payload.available,
    }
    menu_items[idx] = updated
    return {
        "status": "success",
        "message": "Блюдо обновлено",
        "data": updated,
    }


@router.patch("/menu/{item_id}")
async def patch_menu_item(item_id: int, payload: MenuItemUpdate):
    """Частичное обновление блюда (PATCH)."""
    idx = _find_index(item_id)
    item = menu_items[idx]
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Не указано ни одного поля для обновления",
            },
        )
    for key, value in update_data.items():
        item[key] = value
    return {
        "status": "success",
        "message": "Блюдо обновлено",
        "data": item,
    }


# ——— DELETE ———

@router.delete("/menu/{item_id}", status_code=200)
async def delete_menu_item(item_id: int):
    """Удалить блюдо."""
    idx = _find_index(item_id)
    removed = menu_items.pop(idx)
    return {
        "status": "success",
        "message": "Блюдо удалено",
        "data": removed,
    }


# ——— AI-анализ аллергенов ———

@router.get("/analyze/{item_id}/{user_allergens}")
async def analyze_allergens(item_id: int, user_allergens: str):
    """AI-анализ аллергенов для блюда."""
    idx = _find_index(item_id)
    dish = menu_items[idx]

    user_allergens_list = [a.strip() for a in user_allergens.split(",") if a.strip()]

    found_allergens = []
    for allergen in user_allergens_list:
        if allergen in dish["allergens"]:
            found_allergens.append(allergen)

    if "орехи" in found_allergens or "морепродукты" in found_allergens:
        safety_level = "danger"
    elif found_allergens:
        safety_level = "warning"
    else:
        safety_level = "safe"

    return {
        "status": "success",
        "dish_name": dish["name"],
        "analysis": {
            "has_allergens": len(found_allergens) > 0,
            "allergens_found": found_allergens,
            "safety_level": safety_level,
            "message": _get_safety_message(safety_level, found_allergens),
        },
    }


def _get_safety_message(level: str, allergens: list) -> str:
    if level == "danger":
        return f"ОПАСНО! Блюдо содержит {', '.join(allergens)}. НЕ РЕКОМЕНДУЕТСЯ к употреблению!"
    if level == "warning":
        return f"ВНИМАНИЕ! Блюдо содержит {', '.join(allergens)}. Будьте осторожны!"
    return "Безопасно! Аллергены не найдены."
