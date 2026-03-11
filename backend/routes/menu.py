"""Маршруты меню и AI-анализа. CRUD для блюд."""
from fastapi import APIRouter, HTTPException

from core.db import create_dish, delete_dish, get_dish, list_dishes, update_dish
from models.schemas import MenuItemBase, MenuItemUpdate

router = APIRouter(prefix="/api", tags=["menu"])


def _not_found(item_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "NOT_FOUND",
            "message": "Блюдо не найдено",
            "item_id": item_id,
        },
    )


@router.get("/menu")
async def get_menu():
    """Получить всё меню."""
    items = list_dishes()
    return {
        "status": "success",
        "data": items,
        "count": len(items),
    }


@router.get("/menu/category/{category}")
async def get_menu_by_category(category: str):
    """Получить блюда по категории."""
    filtered = list_dishes(category=category, only_available=True)
    return {
        "status": "success",
        "category": category,
        "data": filtered,
        "count": len(filtered),
    }


@router.get("/menu/{item_id}")
async def get_menu_item(item_id: int):
    """Получить блюдо по ID."""
    dish = get_dish(item_id)
    if not dish:
        raise _not_found(item_id)
    return {
        "status": "success",
        "data": dish,
    }


@router.post("/menu", status_code=201)
async def create_menu_item(payload: MenuItemBase):
    """Создать новое блюдо."""
    new_item = create_dish(payload.model_dump())
    return {
        "status": "success",
        "message": "Блюдо создано",
        "data": new_item,
    }


@router.put("/menu/{item_id}")
async def update_menu_item(item_id: int, payload: MenuItemBase):
    """Полное обновление блюда (PUT)."""
    updated = update_dish(item_id, payload.model_dump())
    if not updated:
        raise _not_found(item_id)
    return {
        "status": "success",
        "message": "Блюдо обновлено",
        "data": updated,
    }


@router.patch("/menu/{item_id}")
async def patch_menu_item(item_id: int, payload: MenuItemUpdate):
    """Частичное обновление блюда (PATCH)."""
    item = get_dish(item_id)
    if not item:
        raise _not_found(item_id)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Не указано ни одного поля для обновления",
            },
        )

    merged = {**item, **update_data}
    merged_payload = MenuItemBase(
        name=merged["name"],
        price=merged["price"],
        weight=merged["weight"],
        category=merged["category"],
        ingredients=merged.get("ingredients") or [],
        allergens=merged.get("allergens") or [],
        calories=merged["calories"],
        available=merged.get("available", True),
    )

    updated = update_dish(item_id, merged_payload.model_dump())
    if not updated:
        raise _not_found(item_id)
    return {
        "status": "success",
        "message": "Блюдо обновлено",
        "data": updated,
    }


@router.delete("/menu/{item_id}", status_code=200)
async def delete_menu_item(item_id: int):
    """Удалить блюдо."""
    removed = delete_dish(item_id)
    if not removed:
        raise _not_found(item_id)
    return {
        "status": "success",
        "message": "Блюдо удалено",
        "data": removed,
    }


@router.get("/analyze/{item_id}/{user_allergens}")
async def analyze_allergens(item_id: int, user_allergens: str):
    """AI-анализ аллергенов для блюда."""
    dish = get_dish(item_id)
    if not dish:
        raise _not_found(item_id)

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